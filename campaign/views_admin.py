# campaign/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CampaignX, CampaignXManager, CampaignXOwner, CampaignXPolitician, CampaignXSupporter
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_deleted_exception, handle_record_not_found_exception
from election.controllers import retrieve_election_id_list_by_year_list, retrieve_upcoming_election_id_list
from election.models import Election, ElectionManager
import json
import operator
from voter.models import retrieve_voter_authority, voter_has_authority, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, positive_value_exists, \
    STATE_CODE_MAP

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def campaign_edit_view(request, campaignx_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)
    campaignx_manager = CampaignXManager()
    campaignx = None
    results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)

    if results['campaignx_found']:
        campaignx = results['campaignx']

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'campaignx':                campaignx,
        'state_list':               sorted_state_list,
        'upcoming_election_list':   upcoming_election_list,
    }
    return render(request, 'campaign/campaignx_edit.html', template_values)


@login_required
def campaign_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = \
        {'partner_organization', 'political_data_manager', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    limit_to_opinions_in_state_code = request.GET.get('limit_to_opinions_in_state_code', '')
    limit_to_opinions_in_this_year = convert_to_int(request.GET.get('limit_to_opinions_in_this_year', 0))
    campaignx_search = request.GET.get('campaignx_search', '')
    campaignx_type_filter = request.GET.get('campaignx_type_filter', '')
    sort_by = request.GET.get('sort_by', '')
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_more = request.GET.get('show_more', False)  # Show up to 1,000 organizations
    show_issues = request.GET.get('show_issues', '')
    show_organizations_without_email = positive_value_exists(request.GET.get('show_organizations_without_email', False))
    show_campaigns_in_draft = \
        positive_value_exists(request.GET.get('show_campaigns_in_draft', False))

    election_years_available = [2022, 2021, 2020, 2019, 2018, 2017, 2016]

    messages_on_stage = get_messages(request)
    campaignx_list_query = CampaignX.objects.all()

    if positive_value_exists(show_campaigns_in_draft):
        campaignx_list_query = campaignx_list_query.filter(in_draft_mode=True)
    else:
        campaignx_list_query = campaignx_list_query.filter(in_draft_mode=False)

    if positive_value_exists(sort_by):
        # if sort_by == "twitter":
        #     campaignx_list_query = \
        #         campaignx_list_query.order_by('organization_name').order_by('-twitter_followers_count')
        # else:
        campaignx_list_query = campaignx_list_query.order_by('-supporters_count')
    else:
        campaignx_list_query = campaignx_list_query.order_by('-supporters_count')

    # if positive_value_exists(show_organizations_without_email):
    #     campaignx_list_query = campaignx_list_query.filter(
    #         Q(organization_email__isnull=True) |
    #         Q(organization_email__exact='')
    #     )

    if positive_value_exists(campaignx_search):
        search_words = campaignx_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(campaign_title__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(campaign_description__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(started_by_voter_we_vote_id__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                campaignx_list_query = campaignx_list_query.filter(final_filters)

    campaignx_count = campaignx_list_query.count()
    messages.add_message(request, messages.INFO,
                         '{campaignx_count:,} campaigns found.'.format(campaignx_count=campaignx_count))

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        campaignx_list = campaignx_list_query[:1000]
    elif positive_value_exists(show_all):
        campaignx_list = campaignx_list_query
    else:
        campaignx_list = campaignx_list_query[:50]

    # Now loop through these organizations and add owners
    modified_campaignx_list = []
    campaignx_manager = CampaignXManager()
    for campaignx in campaignx_list:
        campaignx.campaignx_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
            campaignx_we_vote_id=campaignx.we_vote_id,
            viewer_is_owner=True)
        modified_campaignx_list.append(campaignx)

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'candidate_we_vote_id':     candidate_we_vote_id,
        'election_years_available': election_years_available,
        'google_civic_election_id': google_civic_election_id,
        'limit_to_opinions_in_state_code': limit_to_opinions_in_state_code,
        'limit_to_opinions_in_this_year': limit_to_opinions_in_this_year,
        'messages_on_stage':        messages_on_stage,
        'campaignx_type_filter':    campaignx_type_filter,
        'campaignx_types':          [],
        'campaignx_list':           modified_campaignx_list,
        'campaignx_search':         campaignx_search,
        'show_all':                 show_all,
        'show_issues':              show_issues,
        'show_more':                show_more,
        'show_organizations_without_email': show_organizations_without_email,
        'show_campaigns_in_draft': show_campaigns_in_draft,
        'sort_by':                  sort_by,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'campaign/campaignx_list.html', template_values)


@login_required
def campaign_supporters_list_view(request, campaignx_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = \
        {'partner_organization', 'political_data_manager', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    limit_to_opinions_in_state_code = request.GET.get('limit_to_opinions_in_state_code', '')
    limit_to_opinions_in_this_year = convert_to_int(request.GET.get('limit_to_opinions_in_this_year', 0))
    campaignx_search = request.GET.get('campaignx_search', '')
    campaignx_type_filter = request.GET.get('campaignx_type_filter', '')
    sort_by = request.GET.get('sort_by', '')
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_more = request.GET.get('show_more', False)  # Show up to 1,000 organizations
    show_issues = request.GET.get('show_issues', '')
    show_supporters_without_endorsements = \
        positive_value_exists(request.GET.get('show_supporters_without_endorsements', False))
    show_supporters_not_visible_to_public = \
        positive_value_exists(request.GET.get('show_supporters_not_visible_to_public', False))

    election_years_available = [2022, 2021, 2020, 2019, 2018, 2017, 2016]

    messages_on_stage = get_messages(request)

    campaignx = CampaignX.objects.get(we_vote_id__iexact=campaignx_we_vote_id)
    campaignx_title = campaignx.campaign_title

    supporters_query = CampaignXSupporter.objects.all()
    supporters_query = supporters_query.filter(campaignx_we_vote_id__iexact=campaignx_we_vote_id)

    if positive_value_exists(show_supporters_without_endorsements):
        pass
    else:
        supporters_query = supporters_query.exclude(
            Q(supporter_endorsement__isnull=True) |
            Q(supporter_endorsement__exact='')
        )

    supporters_query = supporters_query.order_by('-date_supported')

    if positive_value_exists(show_supporters_not_visible_to_public):
        pass
    else:
        # Default to only show visible_to_public
        supporters_query = supporters_query.filter(visible_to_public=True)

    # if positive_value_exists(state_code):
    #     supporters_query = supporters_query.filter(state_served_code__iexact=state_code)
    #
    # if positive_value_exists(campaignx_type_filter):
    #     if campaignx_type_filter == UNKNOWN:
    #         # Make sure to also show organizations that are not specified
    #         supporters_query = supporters_query.filter(
    #             Q(organization_type__iexact=campaignx_type_filter) |
    #             Q(organization_type__isnull=True) |
    #             Q(organization_type__exact='')
    #         )
    #     else:
    #         supporters_query = supporters_query.filter(organization_type__iexact=campaignx_type_filter)
    # else:
    #     # By default, don't show individuals
    #     supporters_query = supporters_query.exclude(organization_type__iexact=INDIVIDUAL)

    if positive_value_exists(campaignx_search):
        search_words = campaignx_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(supporter_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(supporter_endorsement__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(voter_we_vote_id__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_we_vote_id__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                supporters_query = supporters_query.filter(final_filters)

    supporters_count = supporters_query.count()
    messages.add_message(request, messages.INFO,
                         'Showing {supporters_count:,} campaign supporters.'.format(supporters_count=supporters_count))

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        supporters_list = supporters_query[:1000]
    elif positive_value_exists(show_all):
        supporters_list = supporters_query
    else:
        supporters_list = supporters_query[:200]

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'campaignx_we_vote_id':     campaignx_we_vote_id,
        'campaignx_search':         campaignx_search,
        'campaignx_title':          campaignx_title,
        'election_years_available': election_years_available,
        'google_civic_election_id': google_civic_election_id,
        'limit_to_opinions_in_state_code': limit_to_opinions_in_state_code,
        'limit_to_opinions_in_this_year': limit_to_opinions_in_this_year,
        'messages_on_stage':        messages_on_stage,
        'campaignx_type_filter':    campaignx_type_filter,
        'campaignx_types':          [],
        'supporters_list':          supporters_list,
        'show_all':                 show_all,
        'show_issues':              show_issues,
        'show_more':                show_more,
        'show_supporters_not_visible_to_public': show_supporters_not_visible_to_public,
        'show_supporters_without_endorsements': show_supporters_without_endorsements,
        'sort_by':                  sort_by,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'campaign/campaignx_supporters_list.html', template_values)
