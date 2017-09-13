# analytics/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import save_organization_daily_metrics, save_organization_election_metrics, \
    save_sitewide_daily_metrics, save_sitewide_election_metrics
from .models import AnalyticsAction, AnalyticsManager, OrganizationDailyMetrics, OrganizationElectionMetrics, \
    SitewideDailyMetrics, SitewideElectionMetrics
from admin_tools.views import redirect_to_sign_in_page
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# We do not protect much of our analytics results - They are open to the public
def analytics_index_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    voter_allowed_to_see_organization_analytics = voter_has_authority(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    sitewide_election_metrics_list = []
    try:
        sitewide_election_metrics_query = SitewideElectionMetrics.objects.using('analytics')\
            .order_by('-election_day_text')
        sitewide_election_metrics_query = sitewide_election_metrics_query[:3]
        sitewide_election_metrics_list = list(sitewide_election_metrics_query)
    except SitewideElectionMetrics.DoesNotExist:
        # This is fine
        pass

    sitewide_daily_metrics_list = []
    try:
        sitewide_daily_metrics_query = SitewideDailyMetrics.objects.using('analytics').order_by('-date_as_integer')
        sitewide_daily_metrics_query = sitewide_daily_metrics_query[:3]
        sitewide_daily_metrics_list = list(sitewide_daily_metrics_query)
    except SitewideDailyMetrics.DoesNotExist:
        # This is fine
        pass

    organization_election_metrics_list = []
    try:
        organization_election_metrics_query = OrganizationElectionMetrics.objects.using('analytics').\
            order_by('-election_day_text')
        organization_election_metrics_query = organization_election_metrics_query[:3]
        organization_election_metrics_list = list(organization_election_metrics_query)
    except OrganizationElectionMetrics.DoesNotExist:
        # This is fine
        pass

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                            messages_on_stage,
        'sitewide_election_metrics_list':               sitewide_election_metrics_list,
        'sitewide_daily_metrics_list':                  sitewide_daily_metrics_list,
        'organization_election_metrics_list':           organization_election_metrics_list,
        'voter_allowed_to_see_organization_analytics':  voter_allowed_to_see_organization_analytics,
        'state_code':                                   state_code,
        'google_civic_election_id':                     google_civic_election_id,
    }
    return render(request, 'analytics/index.html', template_values)


@login_required
def organization_daily_metrics_process_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    date_as_integer = 20170904

    if not positive_value_exists(date_as_integer):
        messages.add_message(request, messages.ERROR, 'date_as_integer required.')
        return HttpResponseRedirect(reverse('analytics:organization_daily_metrics', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    results = save_organization_daily_metrics(date_as_integer)
    # kind_of_batch = results['kind_of_batch']
    #
    # messages.add_message(request, messages.INFO, 'Batch Actions:'
    #                                              'Batch kind:{kind_of_batch}, '
    #                                              'Created:{created} '
    #                                              ''.format(kind_of_batch=kind_of_batch,
    #                                                        created=results['number_of_batch_actions_created']))

    return HttpResponseRedirect(reverse('analytics:organization_daily_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def analytics_action_list_view(request, voter_we_vote_id=False, organization_we_vote_id=False):
    """

    :param request:
    :param voter_we_vote_id:
    :param organization_we_vote_id:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    analytics_action_search = request.GET.get('analytics_action_search', '')

    analytics_action_list = []

    messages_on_stage = get_messages(request)
    try:
        analytics_action_query = AnalyticsAction.objects.using('analytics').order_by('-id')
        if positive_value_exists(voter_we_vote_id):
            analytics_action_query = analytics_action_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
        if positive_value_exists(organization_we_vote_id):
            analytics_action_query = analytics_action_query.filter(
                organization_we_vote_id__iexact=organization_we_vote_id)

        if positive_value_exists(analytics_action_search):
            search_words = analytics_action_search.split()
            for one_word in search_words:
                filters = []
                new_filter = Q(voter_we_vote_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(organization_we_vote_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(ballot_item_we_vote_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(google_civic_election_id__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    analytics_action_query = analytics_action_query.filter(final_filters)

        if positive_value_exists(voter_we_vote_id) or positive_value_exists(organization_we_vote_id):
            analytics_action_query = analytics_action_query[:500]
        else:
            analytics_action_query = analytics_action_query[:100]
        analytics_action_list = list(analytics_action_query)
    except OrganizationDailyMetrics.DoesNotExist:
        # This is fine
        pass

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'analytics_action_list':    analytics_action_list,
        'analytics_action_search':  analytics_action_search,
        'google_civic_election_id': google_civic_election_id,
        'state_code':               state_code,
        'organization_we_vote_id':  organization_we_vote_id,
        'voter_we_vote_id':         voter_we_vote_id,
    }
    return render(request, 'analytics/analytics_action_list.html', template_values)


@login_required
def organization_daily_metrics_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    organization_daily_metrics_list = []

    messages_on_stage = get_messages(request)
    try:
        organization_daily_metrics_query = OrganizationDailyMetrics.objects.using('analytics').\
            order_by('-date_as_integer')
        organization_daily_metrics_list = list(organization_daily_metrics_query)
    except OrganizationDailyMetrics.DoesNotExist:
        # This is fine
        pass

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'organization_daily_metrics_list':  organization_daily_metrics_list,
        'google_civic_election_id':         google_civic_election_id,
        'state_code':                       state_code,
    }
    return render(request, 'analytics/organization_daily_metrics.html', template_values)


@login_required
def organization_election_metrics_process_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    organization_we_vote_id = 'wv02org1496'

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'google_civic_election_id required.')
        return HttpResponseRedirect(reverse('analytics:organization_election_metrics', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    results = save_organization_election_metrics(google_civic_election_id, organization_we_vote_id)
    # kind_of_batch = results['kind_of_batch']
    #
    # messages.add_message(request, messages.INFO, 'Batch Actions:'
    #                                              'Batch kind:{kind_of_batch}, '
    #                                              'Created:{created} '
    #                                              ''.format(kind_of_batch=kind_of_batch,
    #                                                        created=results['number_of_batch_actions_created']))

    return HttpResponseRedirect(reverse('analytics:organization_election_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def organization_election_metrics_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    organization_election_metrics_list = []
    try:
        organization_election_metrics_query = OrganizationElectionMetrics.objects.using('analytics').\
            order_by('-election_day_text')
        organization_election_metrics_list = list(organization_election_metrics_query)
    except OrganizationElectionMetrics.DoesNotExist:
        # This is fine
        pass

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'organization_election_metrics_list':   organization_election_metrics_list,
        'google_civic_election_id':             google_civic_election_id,
        'state_code':                           state_code,
    }
    return render(request, 'analytics/organization_election_metrics.html', template_values)


@login_required
def sitewide_daily_metrics_process_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    date_as_integer = 20170904

    if not positive_value_exists(date_as_integer):
        messages.add_message(request, messages.ERROR, 'date_as_integer required.')
        return HttpResponseRedirect(reverse('analytics:sitewide_daily_metrics', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    results = save_sitewide_daily_metrics(date_as_integer)
    # kind_of_batch = results['kind_of_batch']
    #
    # messages.add_message(request, messages.INFO, 'Batch Actions:'
    #                                              'Batch kind:{kind_of_batch}, '
    #                                              'Created:{created} '
    #                                              ''.format(kind_of_batch=kind_of_batch,
    #                                                        created=results['number_of_batch_actions_created']))

    return HttpResponseRedirect(reverse('analytics:sitewide_daily_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def sitewide_daily_metrics_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    sitewide_daily_metrics_list = []

    messages_on_stage = get_messages(request)
    try:
        sitewide_daily_metrics_query = SitewideDailyMetrics.objects.using('analytics').order_by('-date_as_integer')
        sitewide_daily_metrics_list = list(sitewide_daily_metrics_query)
    except SitewideDailyMetrics.DoesNotExist:
        # This is fine
        pass

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'sitewide_daily_metrics_list':  sitewide_daily_metrics_list,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
    }
    return render(request, 'analytics/sitewide_daily_metrics.html', template_values)


@login_required
def sitewide_election_metrics_process_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    date_as_integer = 20170904

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'google_civic_election_id required.')
        return HttpResponseRedirect(reverse('analytics:sitewide_election_metrics', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    results = save_sitewide_election_metrics(google_civic_election_id)
    # kind_of_batch = results['kind_of_batch']
    #
    # messages.add_message(request, messages.INFO, 'Batch Actions:'
    #                                              'Batch kind:{kind_of_batch}, '
    #                                              'Created:{created} '
    #                                              ''.format(kind_of_batch=kind_of_batch,
    #                                                        created=results['number_of_batch_actions_created']))

    return HttpResponseRedirect(reverse('analytics:sitewide_election_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def sitewide_election_metrics_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    sitewide_election_metrics_list = []

    messages_on_stage = get_messages(request)
    try:
        sitewide_election_metrics_query = SitewideElectionMetrics.objects.using('analytics').\
            order_by('-election_day_text')
        sitewide_election_metrics_list = list(sitewide_election_metrics_query)
    except SitewideElectionMetrics.DoesNotExist:
        # This is fine
        pass

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'sitewide_election_metrics_list':   sitewide_election_metrics_list,
        'google_civic_election_id':         google_civic_election_id,
        'state_code':                       state_code,
    }
    return render(request, 'analytics/sitewide_election_metrics.html', template_values)


@login_required
def update_election_summaries_process_view(request):
    """
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    date = 20170905

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'google_civic_election_id required.')
        return HttpResponseRedirect(reverse('analytics:analytics_index', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    analytics_manager = AnalyticsManager()
    results = analytics_manager.retrieve_organization_list_with_election_activity(google_civic_election_id)
    if results['organization_list_found']:
        organization_list = results['organization_list']
        for organization in organization_list:
            save_organization_election_metrics(google_civic_election_id, organization.we_vote_id)
            save_organization_daily_metrics(organization.we_vote_id, date)

    # kind_of_batch = results['kind_of_batch']
    #
    # messages.add_message(request, messages.INFO, 'Batch Actions:'
    #                                              'Batch kind:{kind_of_batch}, '
    #                                              'Created:{created} '
    #                                              ''.format(kind_of_batch=kind_of_batch,
    #                                                        created=results['number_of_batch_actions_created']))

    return HttpResponseRedirect(reverse('analytics:analytics_index', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))
