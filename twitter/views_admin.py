# twitter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from .controllers import delete_possible_twitter_handles, retrieve_possible_twitter_handles
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaign, CandidateCampaignManager
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.utils.timezone import now
from django.http import HttpResponseRedirect
from office.models import ContestOfficeManager
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists
import wevote_functions.admin
from wevote_settings.models import RemoteRequestHistory, RETRIEVE_POSSIBLE_TWITTER_HANDLES
from .models import TwitterLinkPossibility

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def delete_possible_twitter_handles_view(request, candidate_campaign_we_vote_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateCampaignManager()
    results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_campaign_we_vote_id)

    if not results['candidate_campaign_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_campaign_we_vote_id,)))

    candidate_campaign = results['candidate_campaign']

    results = delete_possible_twitter_handles(candidate_campaign)
    messages.add_message(request, messages.INFO, 'Possibilities deleted.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))


@login_required
def retrieve_possible_twitter_handles_view(request, candidate_campaign_we_vote_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateCampaignManager()
    results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_campaign_we_vote_id)

    if not results['candidate_campaign_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_campaign_we_vote_id,)))

    candidate_campaign = results['candidate_campaign']

    results = retrieve_possible_twitter_handles(candidate_campaign)
    messages.add_message(request, messages.INFO, 'Number of possibilities found: ' + results['num_of_possibilities'])

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))


@login_required
def bulk_retrieve_possible_twitter_handles_view(request):
    success = True
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = request.GET.get('hide_candidate_tools', False)
    page = request.GET.get('page', 0)
    state_code = request.GET.get('state_code', '')
    limit = convert_to_int(request.GET.get('show_all', 0))
    office_manager = ContestOfficeManager() #newcode_addbyAlice

    if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code) \
            and not positive_value_exists(limit):
        messages.add_message(request, messages.ERROR,
                             'bulk_retrieve_possible_twitter_handles_view, LIMITING_VARIABLE_REQUIRED')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )
    #editedbyAlice
    status = ""
    try:
        candidate_queryset = CandidateCampaign.objects.all()
        office_visiting_we_vote_ids = office_manager.fetch_office_visiting_list_we_vote_ids(
            host_google_civic_election_id_list=[google_civic_election_id])
        if positive_value_exists(google_civic_election_id):
            candidate_queryset = candidate_queryset.filter()
            candidate_queryset = candidate_queryset.filter(
                Q(google_civic_election_id=google_civic_election_id) |
                Q(contest_office_we_vote_id=office_visiting_we_vote_ids))
            candidate_queryset = candidate_queryset.filter(
                Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle=""))
         # Exclude candidates we have already have TwitterLinkPossibility data for
        try:
            twitter_possibility_list = TwitterLinkPossibility.objects. \
                values_list('candidate_campaign_we_vote_id', flat=True).distinct()
            if len(twitter_possibility_list):
                candidate_queryset = candidate_queryset.exclude(we_vote_id__in=twitter_possibility_list)
        except Exception as e:
            status += "PROBLEM_RETRIEVING_TWITTER_LINK_POSSIBILITY " + str(e) + " "
        # Exclude candidates we have requested information for in the last month
        try:
        # Exclude candidates searched for in the last month
            remote_request_query = RemoteRequestHistory.objects.all()
            one_month_of_seconds = 60 * 60 * 24 * 30  # 60 seconds, 60 minutes, 24 hours, 30 days
            one_month_ago = now() - timedelta(seconds=one_month_of_seconds)
            remote_request_query = remote_request_query.filter(datetime_of_action__gt=one_month_ago)
            remote_request_query = remote_request_query.filter(kind_of_action__iexact=RETRIEVE_POSSIBLE_TWITTER_HANDLES)
            remote_request_list = remote_request_query.values_list('candidate_campaign_we_vote_id', flat=True).distinct()
            if len(remote_request_list):
                candidate_queryset = candidate_queryset.exclude(we_vote_id__in=remote_request_list)
        except Exception as e:
            status += "PROBLEM_RETRIEVING_TWITTER_LINK_POSSIBILITY " + str(e) + " "
        if positive_value_exists(state_code): #didn't remove this part because the function didn't include state
            candidate_queryset = candidate_queryset.filter(state_code__iexact=state_code)
        candidate_queryset = candidate_queryset.order_by('candidate_name')
        if positive_value_exists(limit):
            candidate_queryset = candidate_queryset[:limit]

        # Run Twitter account search and analysis on candidates without a linked or possible Twitter account
        number_of_candidates_limit = 20
        candidates_to_analyze = candidate_queryset.count()
        candidate_list = candidate_queryset[:number_of_candidates_limit]

        candidates_analyzed = 0
        status += "RETRIEVE_POSSIBLE_TWITTER_HANDLES_LOOP-TOTAL: " + str(candidates_to_analyze) + " "
        for one_candidate in candidate_list:
        # Twitter account search and analysis has not been run on this candidate yet
            results = retrieve_possible_twitter_handles(one_candidate)
            if results['success']:
                candidates_analyzed += 1
            status += results['status']

        results = {
            'success':                  success,
            'status':                   status,
            'candidates_to_analyze':    candidates_to_analyze,
            'candidates_analyzed':      candidates_analyzed,
            }
    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        pass

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code) +
                                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                '&page=' + str(page)
                                )
