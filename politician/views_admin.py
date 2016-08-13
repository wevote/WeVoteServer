# politician/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Politician, PoliticianManager
from .serializers import PoliticianSerializer
from admin_tools.views import redirect_to_sign_in_page
from office.models import ContestOffice, ContestOfficeManager
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception, print_to_log
from import_export_vote_smart.models import VoteSmartRatingOneCandidate
from import_export_vote_smart.votesmart_local import VotesmartApiError
from position.models import PositionEntered, PositionListManager
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, \
    positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
class CandidatesSyncOutView(APIView):
    def get(self, request, format=None):
        state_code = request.GET.get('state_code', '')

        politician_list = Politician.objects.all()
        if positive_value_exists(state_code):
            politician_list = politician_list.filter(state_code=state_code)

        serializer = PoliticianSerializer(politician_list, many=True)
        return Response(serializer.data)


@login_required
def politician_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    politician_search = request.GET.get('politician_search', '')
    politician_list = []

    try:
        politician_list = Politician.objects.all()
        if positive_value_exists(state_code):
            politician_list = politician_list.filter(state_code=state_code)

        filters = []
        if positive_value_exists(politician_search):
            new_filter = Q(politician_name__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_twitter_handle__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(party__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__icontains=politician_search)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                politician_list = politician_list.filter(final_filters)

        politician_list = politician_list.order_by('politician_name')[:200]
    except ObjectDoesNotExist:
        # This is fine, create new
        pass

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage':    messages_on_stage,
        'politician_list':      politician_list,
        'politician_search':    politician_search,
        'election_list':        election_list,
        'state_code':           state_code,
    }
    return render(request, 'politician/politician_list.html', template_values)


@login_required
def candidate_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    contest_office_id = request.GET.get('contest_office_id', 0)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    candidate_name = request.GET.get('candidate_name', "")
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', "")
    state_code = request.GET.get('state_code', "")
    candidate_twitter_handle = request.GET.get('candidate_twitter_handle', "")
    candidate_url = request.GET.get('candidate_url', "")
    party = request.GET.get('party', "")
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', "")
    vote_smart_id = request.GET.get('vote_smart_id', "")
    maplight_id = request.GET.get('maplight_id', "")
    politician_we_vote_id = request.GET.get('politician_we_vote_id', "")

    # These are the Offices already entered for this election
    try:
        contest_office_list = ContestOffice.objects.order_by('office_name')
        contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        contest_office_list = []

    # Its helpful to see existing candidates when entering a new candidate
    candidate_list = []
    try:
        candidate_list = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(contest_office_id):
            candidate_list = candidate_list.filter(contest_office_id=contest_office_id)
        candidate_list = candidate_list.order_by('candidate_name')[:500]
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    election_manager = ElectionManager()
    election_results = election_manager.retrieve_election(google_civic_election_id)
    state_code_from_election = ""
    if election_results['election_found']:
        election = election_results['election']
        election_found = election_results['election_found']
        state_code_from_election = election.get_election_state()

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'office_list':              contest_office_list,
        'contest_office_id':        contest_office_id,  # We need to always pass in separately for the template to work
        'google_civic_election_id': google_civic_election_id,
        'candidate_list':           candidate_list,
        'state_code_from_election': state_code_from_election,
        # Incoming variables, not saved yet
        'candidate_name':                   candidate_name,
        'google_civic_candidate_name':      google_civic_candidate_name,
        'state_code':                       state_code,
        'candidate_twitter_handle':         candidate_twitter_handle,
        'candidate_url':                    candidate_url,
        'party':                            party,
        'ballot_guide_official_statement':  ballot_guide_official_statement,
        'vote_smart_id':                    vote_smart_id,
        'maplight_id':                      maplight_id,
        'politician_we_vote_id':            politician_we_vote_id,
    }
    return render(request, 'candidate/candidate_edit.html', template_values)


@login_required
def candidate_edit_view(request, candidate_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    candidate_name = request.GET.get('candidate_name', False)
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', False)
    candidate_twitter_handle = request.GET.get('candidate_twitter_handle', False)
    candidate_url = request.GET.get('candidate_url', False)
    party = request.GET.get('party', False)
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', False)
    vote_smart_id = request.GET.get('vote_smart_id', False)
    maplight_id = request.GET.get('maplight_id', False)

    messages_on_stage = get_messages(request)
    candidate_id = convert_to_int(candidate_id)
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    contest_office_id = 0
    google_civic_election_id = 0

    try:
        candidate_on_stage = CandidateCampaign.objects.get(id=candidate_id)
        candidate_on_stage_found = True
        contest_office_id = candidate_on_stage.contest_office_id
        google_civic_election_id = candidate_on_stage.google_civic_election_id
    except CandidateCampaign.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new below
        pass

    if candidate_on_stage_found:
        # Working with Vote Smart data
        try:
            vote_smart_candidate_id = candidate_on_stage.vote_smart_id
            rating_list_query = VoteSmartRatingOneCandidate.objects.order_by('-timeSpan')  # Desc order
            rating_list = rating_list_query.filter(candidateId=vote_smart_candidate_id)
        except VotesmartApiError as error_instance:
            # Catch the error message coming back from Vote Smart and pass it in the status
            error_message = error_instance.args
            status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
            print_to_log(logger=logger, exception_message_optional=status)
            rating_list = []

        # Working with We Vote Positions
        try:
            candidate_position_list = PositionEntered.objects.order_by('stance')
            candidate_position_list = candidate_position_list.filter(candidate_campaign_id=candidate_id)
            # if positive_value_exists(google_civic_election_id):
            #     organization_position_list = candidate_position_list.filter(
            #         google_civic_election_id=google_civic_election_id)
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            candidate_position_list = []

        # Working with Offices for this election
        try:
            contest_office_list = ContestOffice.objects.order_by('office_name')
            contest_office_list = contest_office_list.filter(
                google_civic_election_id=candidate_on_stage.google_civic_election_id)
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            contest_office_list = []

        template_values = {
            'messages_on_stage':        messages_on_stage,
            'candidate':                candidate_on_stage,
            'rating_list':              rating_list,
            'candidate_position_list':  candidate_position_list,
            'office_list':              contest_office_list,
            'contest_office_id':        contest_office_id,
            'google_civic_election_id': google_civic_election_id,
            # Incoming variables, not saved yet
            'candidate_name':                   candidate_name,
            'google_civic_candidate_name':      google_civic_candidate_name,
            'candidate_twitter_handle':         candidate_twitter_handle,
            'candidate_url':                    candidate_url,
            'party':                            party,
            'ballot_guide_official_statement':  ballot_guide_official_statement,
            'vote_smart_id':                    vote_smart_id,
            'maplight_id':                      maplight_id,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            # Incoming variables
            'vote_smart_id':        vote_smart_id,
        }
    return render(request, 'candidate/candidate_edit.html', template_values)


@login_required
def candidate_edit_process_view(request):
    """
    Process the new or edit candidate forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    look_for_politician = request.POST.get('look_for_politician', False)  # If this comes in with value, don't save
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)

    candidate_id = convert_to_int(request.POST['candidate_id'])
    candidate_name = request.POST.get('candidate_name', False)
    google_civic_candidate_name = request.POST.get('google_civic_candidate_name', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    candidate_twitter_handle = request.POST.get('candidate_twitter_handle', False)
    if positive_value_exists(candidate_twitter_handle):
        candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle)
    candidate_url = request.POST.get('candidate_url', False)
    contest_office_id = request.POST.get('contest_office_id', False)
    ballot_guide_official_statement = request.POST.get('ballot_guide_official_statement', False)
    party = request.POST.get('party', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    maplight_id = request.POST.get('maplight_id', False)
    state_code = request.POST.get('state_code', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)

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
            pass

    contest_office_we_vote_id = ''
    if positive_value_exists(contest_office_id):
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office_from_id(contest_office_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            contest_office_we_vote_id = contest_office.we_vote_id

    election_manager = ElectionManager()
    election_results = election_manager.retrieve_election(google_civic_election_id)
    state_code_from_election = ""
    if election_results['election_found']:
        election = election_results['election']
        election_found = election_results['election_found']
        state_code_from_election = election.get_election_state()

    best_state_code = state_code_from_election if positive_value_exists(state_code_from_election) \
        else state_code

    if positive_value_exists(look_for_politician):
        # If here, we specifically want to see if a politician exists, given the information submitted
        match_results = retrieve_candidate_politician_match_options(vote_smart_id, maplight_id,
                                                                    candidate_twitter_handle,
                                                                    candidate_name, best_state_code)
        if match_results['politician_found']:
            messages.add_message(request, messages.INFO, 'Politician found! Information filled into this form.')
            matching_politician = match_results['politician']
            politician_we_vote_id = matching_politician.we_vote_id
            politician_twitter_handle = matching_politician.politician_twitter_handle \
                if positive_value_exists(matching_politician.politician_twitter_handle) else ""
            # If Twitter handle was entered in the Add new form, leave in place. Otherwise, pull from Politician entry.
            candidate_twitter_handle = candidate_twitter_handle if candidate_twitter_handle \
                else politician_twitter_handle
            vote_smart_id = matching_politician.vote_smart_id
            maplight_id = matching_politician.maplight_id if positive_value_exists(matching_politician.maplight_id) \
                else ""
            party = matching_politician.political_party
            google_civic_candidate_name = matching_politician.google_civic_candidate_name
            candidate_name = candidate_name if positive_value_exists(candidate_name) \
                else matching_politician.politician_name
        else:
            messages.add_message(request, messages.INFO, 'No politician found. Please make sure you have entered '
                                                         '1) Candidate Name & State Code, '
                                                         '2) Twitter Handle, or '
                                                         '3) Vote Smart Id')

        url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                        "&candidate_name=" + str(candidate_name) + \
                        "&state_code=" + str(state_code) + \
                        "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                        "&contest_office_id=" + str(contest_office_id) + \
                        "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                        "&candidate_url=" + str(candidate_url) + \
                        "&party=" + str(party) + \
                        "&ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                        "&vote_smart_id=" + str(vote_smart_id) + \
                        "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                        "&maplight_id=" + str(maplight_id)

        if positive_value_exists(candidate_id):
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) + url_variables)
        else:
            return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) + url_variables)

    # Check to see if there is a duplicate candidate already saved for this election
    existing_candidate_found = False
    if not positive_value_exists(candidate_id):
        try:
            filter_list = Q()

            at_least_one_filter = False
            if positive_value_exists(vote_smart_id):
                at_least_one_filter = True
                filter_list |= Q(vote_smart_id=vote_smart_id)
            if positive_value_exists(maplight_id):
                at_least_one_filter = True
                filter_list |= Q(maplight_id=maplight_id)

            if at_least_one_filter:
                candidate_duplicates_query = CandidateCampaign.objects.filter(filter_list)
                candidate_duplicates_query = candidate_duplicates_query.filter(
                    google_civic_election_id=google_civic_election_id)

                if len(candidate_duplicates_query):
                    existing_candidate_found = True
        except Exception as e:
            pass

    try:
        if existing_candidate_found:
            messages.add_message(request, messages.ERROR, 'This candidate is already saved for this election.')
            url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                            "&candidate_name=" + str(candidate_name) + \
                            "&state_code=" + str(state_code) + \
                            "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                            "&contest_office_id=" + str(contest_office_id) + \
                            "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                            "&candidate_url=" + str(candidate_url) + \
                            "&party=" + str(party) + \
                            "&ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                            "&vote_smart_id=" + str(vote_smart_id) + \
                            "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                            "&maplight_id=" + str(maplight_id)
            return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) + url_variables)
        elif candidate_on_stage_found:
            # Update
            if candidate_twitter_handle is not False:
                candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
            if candidate_url is not False:
                candidate_on_stage.candidate_url = candidate_url
            if ballot_guide_official_statement is not False:
                candidate_on_stage.ballot_guide_official_statement = ballot_guide_official_statement
            if party is not False:
                candidate_on_stage.party = party

            # Check to see if this is a We Vote-created election
            # is_we_vote_google_civic_election_id = True \
            #     if convert_to_int(candidate_on_stage.google_civic_election_id) >= 1000000 \
            #     else False

            if contest_office_id is not False:
                # We only allow updating of candidates within the We Vote Admin in
                candidate_on_stage.contest_office_id = contest_office_id
                candidate_on_stage.contest_office_we_vote_id = contest_office_we_vote_id
            candidate_on_stage.save()
            messages.add_message(request, messages.INFO, 'Candidate Campaign updated.')
        else:
            # Create new
            # election must be found
            if not election_found:
                messages.add_message(request, messages.ERROR, 'Could not find election -- required to save candidate.')
                return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

            required_candidate_variables = True \
                if positive_value_exists(candidate_name) and positive_value_exists(contest_office_id) \
                else False
            if required_candidate_variables:
                candidate_on_stage = CandidateCampaign(
                    candidate_name=candidate_name,
                    google_civic_election_id=google_civic_election_id,
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    state_code=best_state_code,
                )
                if google_civic_candidate_name is not False:
                    candidate_on_stage.google_civic_candidate_name = google_civic_candidate_name
                if candidate_twitter_handle is not False:
                    candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
                if candidate_url is not False:
                    candidate_on_stage.candidate_url = candidate_url
                if party is not False:
                    candidate_on_stage.party = party
                if ballot_guide_official_statement is not False:
                    candidate_on_stage.ballot_guide_official_statement = ballot_guide_official_statement
                if vote_smart_id is not False:
                    candidate_on_stage.vote_smart_id = vote_smart_id
                if maplight_id is not False:
                    candidate_on_stage.maplight_id = maplight_id
                if politician_we_vote_id is not False:
                    candidate_on_stage.politician_we_vote_id = politician_we_vote_id

                candidate_on_stage.save()
                candidate_id = candidate_on_stage.id
                messages.add_message(request, messages.INFO, 'New candidate saved.')
            else:
                # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
                url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                                "&candidate_name=" + str(candidate_name) + \
                                "&state_code=" + str(state_code) + \
                                "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                                "&contest_office_id=" + str(contest_office_id) + \
                                "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                                "&candidate_url=" + str(candidate_url) + \
                                "&party=" + str(party) + \
                                "&ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                                "&vote_smart_id=" + str(vote_smart_id) + \
                                "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                                "&maplight_id=" + str(maplight_id)
                if positive_value_exists(candidate_id):
                    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                                url_variables)
                else:
                    return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) +
                                                url_variables)

    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save candidate.')
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('candidate:find_and_remove_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))
    else:
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))
