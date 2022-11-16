# analytics/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import augment_one_voter_analytics_action_entries_without_election_id, \
    augment_voter_analytics_action_entries_without_election_id, \
    save_organization_daily_metrics, save_organization_election_metrics, \
    save_sitewide_daily_metrics, save_sitewide_election_metrics, save_sitewide_voter_metrics
from .models import ACTION_WELCOME_VISIT, AnalyticsAction, AnalyticsManager, display_action_constant_human_readable, \
    fetch_action_constant_number_from_constant_string, OrganizationDailyMetrics, OrganizationElectionMetrics, \
    SitewideDailyMetrics, SitewideElectionMetrics, SitewideVoterMetrics
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
import csv
from datetime import date, datetime, timedelta
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from django.utils.timezone import now
from election.models import Election, ElectionManager
from exception.models import print_to_log
import json
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_date_as_integer_to_date, convert_date_to_date_as_integer, \
    convert_date_to_we_vote_date_string, convert_to_int, positive_value_exists
from wevote_settings.models import WeVoteSetting, WeVoteSettingsManager

logger = wevote_functions.admin.get_logger(__name__)

ANALYTICS_ACTION_SYNC_URL = "https://api.wevoteusa.org/apis/v1/analyticsActionSyncOut/"
ORGANIZATION_ELECTION_METRICS_SYNC_URL = "https://api.wevoteusa.org/apis/v1/organizationElectionMetricsSyncOut/"
SITEWIDE_DAILY_METRICS_SYNC_URL = "https://api.wevoteusa.org/apis/v1/sitewideDailyMetricsSyncOut/"
SITEWIDE_ELECTION_METRICS_SYNC_URL = "https://api.wevoteusa.org/apis/v1/sitewideElectionMetricsSyncOut/"
SITEWIDE_VOTER_METRICS_SYNC_URL = "https://api.wevoteusa.org/apis/v1/sitewideVoterMetricsSyncOut/"
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")


def analytics_action_sync_out_view(request):  # analyticsActionSyncOut
    status = ''
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'analytics_admin'}
    if not voter_has_authority(request, authority_required):
        json_data = {
            'success': False,
            'status': 'ANALYTICS_ACTION_SYNC_OUT-NOT_ANALYTICS_ADMIN '
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    starting_date_as_integer = convert_to_int(request.GET.get('starting_date_as_integer', 0))
    ending_date_as_integer = convert_to_int(request.GET.get('ending_date_as_integer', 0))
    return_csv_format = positive_value_exists(request.GET.get('return_csv_format', False))

    generated_starting_date_as_integer = 0

    try:
        analytics_action_query = AnalyticsAction.objects.all().order_by('-id')
        if positive_value_exists(starting_date_as_integer):
            analytics_action_query = analytics_action_query.filter(date_as_integer__gte=starting_date_as_integer)
        else:
            one_month_ago = now() - timedelta(days=30)
            generated_starting_date_as_integer = convert_date_to_date_as_integer(one_month_ago)
            analytics_action_query = analytics_action_query.filter(
                date_as_integer__gte=generated_starting_date_as_integer)
        if positive_value_exists(ending_date_as_integer):
            analytics_action_query = analytics_action_query.filter(date_as_integer__lte=ending_date_as_integer)
        # else:
        #     # By default only return up to two days ago, so we are sure that the post-processing is done
        #     yesterday = now() - timedelta(days=1)
        #     generated_ending_date_as_integer = convert_date_to_date_as_integer(yesterday)
        #     analytics_action_query = analytics_action_query.filter(
        #         date_as_integer__lte=generated_ending_date_as_integer)

        analytics_action_query = analytics_action_query.extra(
            select={'exact_time': "to_char(exact_time, 'YYYY-MM-DD HH24:MI:SS')"})
        analytics_action_list_dict = analytics_action_query.values(
            'id', 'action_constant', 'authentication_failed_twice',
            'ballot_item_we_vote_id', 'date_as_integer',
            'exact_time', 'first_visit_today', 'google_civic_election_id',
            'is_bot', 'is_desktop', 'is_mobile', 'is_signed_in', 'is_tablet',
            'organization_we_vote_id', 'state_code', 'user_agent', 'voter_we_vote_id')
        if analytics_action_list_dict:
            analytics_action_list_raw = list(analytics_action_list_dict)
            if return_csv_format:
                # Create the HttpResponse object with the appropriate CSV header.
                filename = "analyticsActionSyncOut"
                if positive_value_exists(starting_date_as_integer):
                    filename += "-" + str(starting_date_as_integer)
                elif positive_value_exists(generated_starting_date_as_integer):
                    filename += "-" + str(generated_starting_date_as_integer)
                if positive_value_exists(ending_date_as_integer):
                    filename += "-" + str(ending_date_as_integer)
                filename += ".csv"
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="' + filename + '"'

                writer = csv.writer(response)
                writer.writerow(['exact_time', 'id', 'action_constant', 'authentication_failed_twice',
                                 'ballot_item_we_vote_id', 'date_as_integer',
                                 'first_visit_today', 'google_civic_election_id',
                                 'is_bot', 'is_desktop', 'is_mobile', 'is_signed_in', 'is_tablet',
                                 'organization_we_vote_id', 'state_code', 'user_agent', 'voter_we_vote_id',
                                 'action_constant_text'])
                for one_dict in analytics_action_list_raw:
                    one_row = list(one_dict.values())
                    one_row.append(display_action_constant_human_readable(one_dict['action_constant']))
                    writer.writerow(one_row)

                return response
            else:
                analytics_action_list_json = []
                for one_dict in analytics_action_list_raw:
                    one_dict['action_constant_text'] = display_action_constant_human_readable(
                        one_dict['action_constant'])
                    analytics_action_list_json.append(one_dict)
                return HttpResponse(json.dumps(analytics_action_list_json), content_type='application/json')
    except Exception as e:
        status += 'QUERY_FAILURE: ' + str(e) + ' '
        success = False

    status += 'ANALYTICS_ACTION_LIST_EMPTY '
    json_data = {
        'success': success,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_daily_metrics_sync_out_view(request):  # organizationDailyMetricsSyncOut
    status = ''
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'analytics_admin'}
    if not voter_has_authority(request, authority_required):
        json_data = {
            'success': False,
            'status': 'ORGANIZATION_DAILY_METRICS_SYNC_OUT-NOT_ANALYTICS_ADMIN '
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    starting_date_as_integer = convert_to_int(request.GET.get('starting_date_as_integer', 0))
    ending_date_as_integer = convert_to_int(request.GET.get('ending_date_as_integer', 0))
    return_csv_format = positive_value_exists(request.GET.get('return_csv_format', False))

    generated_starting_date_as_integer = 0

    try:
        metrics_query = OrganizationDailyMetrics.objects.all().order_by('-id')
        if positive_value_exists(starting_date_as_integer):
            metrics_query = metrics_query.filter(date_as_integer__gte=starting_date_as_integer)
        else:
            one_month_ago = now() - timedelta(days=30)
            generated_starting_date_as_integer = convert_date_to_date_as_integer(one_month_ago)
            metrics_query = metrics_query.filter(
                date_as_integer__gte=generated_starting_date_as_integer)
        if positive_value_exists(ending_date_as_integer):
            metrics_query = metrics_query.filter(date_as_integer__lte=ending_date_as_integer)

        metrics_list_dict = metrics_query.values(
            'id', 'authenticated_visitors_today', 'authenticated_visitors_total', 'auto_followers_total',
            'date_as_integer', 'entrants_visiting_ballot',
            'followers_total', 'followers_visiting_ballot',
            'issues_linked_total', 'new_auto_followers_today', 'new_followers_today', 'new_visitors_today',
            'organization_public_positions', 'organization_we_vote_id',
            'visitors_today', 'visitors_total', 'voter_guide_entrants', 'voter_guide_entrants_today'
        )
        if metrics_list_dict:
            metrics_list_raw = list(metrics_list_dict)
            if return_csv_format:
                # Create the HttpResponse object with the appropriate CSV header.
                filename = "organizationDailyMetricsSyncOut"
                if positive_value_exists(starting_date_as_integer):
                    filename += "-" + str(starting_date_as_integer)
                elif positive_value_exists(generated_starting_date_as_integer):
                    filename += "-" + str(generated_starting_date_as_integer)
                if positive_value_exists(ending_date_as_integer):
                    filename += "-" + str(ending_date_as_integer)
                filename += ".csv"
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="' + filename + '"'

                writer = csv.writer(response)
                writer.writerow(
                    [
                        'id', 'authenticated_visitors_today', 'authenticated_visitors_total', 'auto_followers_total',
                        'date_as_integer', 'entrants_visiting_ballot', 'exact_time',
                        'followers_total', 'followers_visiting_ballot',
                        'issues_linked_total', 'new_auto_followers_today', 'new_followers_today', 'new_visitors_today',
                        'organization_public_positions', 'organization_we_vote_id',
                        'visitors_today', 'visitors_total', 'voter_guide_entrants', 'voter_guide_entrants_today'
                    ])
                for one_dict in metrics_list_raw:
                    one_row = list(one_dict.values())
                    writer.writerow(one_row)

                return response
            else:
                analytics_action_list_json = []
                for one_dict in metrics_list_raw:
                    analytics_action_list_json.append(one_dict)
                return HttpResponse(json.dumps(analytics_action_list_json), content_type='application/json')
    except Exception as e:
        status += 'QUERY_FAILURE: ' + str(e) + ' '
        success = False

    status += 'ORGANIZATION_DAILY_METRICS_LIST_EMPTY '
    json_data = {
        'success': success,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_election_metrics_sync_out_view(request):  # organizationElectionMetricsSyncOut
    status = ''
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'analytics_admin'}
    if not voter_has_authority(request, authority_required):
        json_data = {
            'success': False,
            'status': 'ORGANIZATION_ELECTION_METRICS_SYNC_OUT-NOT_ANALYTICS_ADMIN '
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    starting_date_as_integer = convert_to_int(request.GET.get('starting_date_as_integer', 0))
    ending_date_as_integer = convert_to_int(request.GET.get('ending_date_as_integer', 0))
    return_csv_format = positive_value_exists(request.GET.get('return_csv_format', False))

    if not positive_value_exists(starting_date_as_integer):
        one_month_ago = now() - timedelta(days=30)
        starting_date_as_integer = convert_date_to_date_as_integer(one_month_ago)

    if not positive_value_exists(ending_date_as_integer):
        time_now = now()
        ending_date_as_integer = convert_date_to_date_as_integer(time_now)

    election_manager = ElectionManager()
    results = election_manager.retrieve_elections_between_dates(
        starting_date_as_integer=starting_date_as_integer,
        ending_date_as_integer=ending_date_as_integer
    )
    election_list = results['election_list']
    google_civic_election_id_list = []
    for one_election in election_list:
        google_civic_election_id_list.append(one_election.google_civic_election_id)

    try:
        metrics_query = OrganizationElectionMetrics.objects.all().order_by('-id')
        metrics_query = metrics_query.filter(google_civic_election_id__in=google_civic_election_id_list)

        metrics_list_dict = metrics_query.values(
            'id', 'authenticated_visitors_total', 'election_day_text',
            'entrants_friends_only_positions', 'entrants_friends_only_positions_with_comments',
            'entrants_public_positions', 'entrants_public_positions_with_comments',
            'entrants_took_position', 'entrants_visited_ballot',
            'followers_at_time_of_election', 'followers_friends_only_positions',
            'followers_friends_only_positions_with_comments', 'followers_public_positions',
            'followers_public_positions_with_comments', 'followers_took_position',
            'followers_visited_ballot', 'google_civic_election_id', 'new_auto_followers', 'new_followers',
            'organization_we_vote_id', 'visitors_total', 'voter_guide_entrants'
        )
        if metrics_list_dict:
            metrics_list_raw = list(metrics_list_dict)
            if return_csv_format:
                # Create the HttpResponse object with the appropriate CSV header.
                filename = "organizationElectionMetricsSyncOut"
                filename += "-" + str(starting_date_as_integer)
                filename += "-" + str(ending_date_as_integer)
                filename += ".csv"
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="' + filename + '"'

                writer = csv.writer(response)
                writer.writerow(
                    [
                        'id', 'authenticated_visitors_total', 'election_day_text',
                        'entrants_friends_only_positions', 'entrants_friends_only_positions_with_comments',
                        'entrants_public_positions', 'entrants_public_positions_with_comments',
                        'entrants_took_position', 'entrants_visited_ballot',
                        'followers_at_time_of_election', 'followers_friends_only_positions',
                        'followers_friends_only_positions_with_comments', 'followers_public_positions',
                        'followers_public_positions_with_comments', 'followers_took_position',
                        'followers_visited_ballot', 'google_civic_election_id', 'new_auto_followers', 'new_followers',
                        'organization_we_vote_id', 'visitors_total', 'voter_guide_entrants'
                    ])
                for one_dict in metrics_list_raw:
                    one_row = list(one_dict.values())
                    writer.writerow(one_row)

                return response
            else:
                analytics_action_list_json = []
                for one_dict in metrics_list_raw:
                    analytics_action_list_json.append(one_dict)
                return HttpResponse(json.dumps(analytics_action_list_json), content_type='application/json')
    except Exception as e:
        status += 'QUERY_FAILURE: ' + str(e) + ' '
        success = False

    status += 'ORGANIZATION_ELECTION_METRICS_LIST_EMPTY '
    json_data = {
        'success': success,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def sitewide_daily_metrics_sync_out_view(request):  # sitewideDailyMetricsSyncOut
    status = ''
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'analytics_admin'}
    if not voter_has_authority(request, authority_required):
        json_data = {
            'success': False,
            'status': 'SITEWIDE_DAILY_METRICS_SYNC_OUT-NOT_ANALYTICS_ADMIN '
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    starting_date_as_integer = convert_to_int(request.GET.get('starting_date_as_integer', 0))
    ending_date_as_integer = convert_to_int(request.GET.get('ending_date_as_integer', 0))
    return_csv_format = positive_value_exists(request.GET.get('return_csv_format', False))

    generated_starting_date_as_integer = 0

    try:
        metrics_query = SitewideDailyMetrics.objects.all().order_by('-id')
        if positive_value_exists(starting_date_as_integer):
            metrics_query = metrics_query.filter(date_as_integer__gte=starting_date_as_integer)
        else:
            one_month_ago = now() - timedelta(days=30)
            generated_starting_date_as_integer = convert_date_to_date_as_integer(one_month_ago)
            metrics_query = metrics_query.filter(
                date_as_integer__gte=generated_starting_date_as_integer)
        if positive_value_exists(ending_date_as_integer):
            metrics_query = metrics_query.filter(date_as_integer__lte=ending_date_as_integer)

        metrics_list_dict = metrics_query.values(
            'id', 'authenticated_visitors_today', 'authenticated_visitors_total',
            'ballot_views_today', 'date_as_integer', 'entered_full_address',
            'friend_entrants_today', 'friends_only_positions',
            'individuals_with_friends_only_positions', 'individuals_with_positions',
            'individuals_with_public_positions',
            'issue_follows_today', 'issue_follows_total',
            'issues_followed_today', 'issues_followed_total',
            'issues_linked_today', 'issues_linked_total',
            'new_visitors_today', 'organization_public_positions',
            'organizations_auto_followed_today', 'organizations_auto_followed_total',
            'organizations_followed_today', 'organizations_followed_total',
            'organizations_signed_in_total', 'organizations_with_linked_issues',
            'organizations_with_new_positions_today', 'organizations_with_positions',
            'visitors_today', 'visitors_total',
            'voter_guide_entrants_today', 'voter_guides_viewed_today',
            'voter_guides_viewed_total', 'welcome_page_entrants_today',
        )
        if metrics_list_dict:
            metrics_list_raw = list(metrics_list_dict)
            if return_csv_format:
                # Create the HttpResponse object with the appropriate CSV header.
                filename = "sitewideDailyMetricsSyncOut"
                if positive_value_exists(starting_date_as_integer):
                    filename += "-" + str(starting_date_as_integer)
                elif positive_value_exists(generated_starting_date_as_integer):
                    filename += "-" + str(generated_starting_date_as_integer)
                if positive_value_exists(ending_date_as_integer):
                    filename += "-" + str(ending_date_as_integer)
                filename += ".csv"
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="' + filename + '"'

                writer = csv.writer(response)
                writer.writerow(
                    [
                        'id', 'authenticated_visitors_today', 'authenticated_visitors_total',
                        'ballot_views_today', 'date_as_integer', 'entered_full_address',
                        'friend_entrants_today', 'friends_only_positions',
                        'individuals_with_friends_only_positions', 'individuals_with_positions',
                        'individuals_with_public_positions',
                        'issue_follows_today', 'issue_follows_total',
                        'issues_followed_today', 'issues_followed_total',
                        'issues_linked_today', 'issues_linked_total',
                        'new_visitors_today', 'organization_public_positions',
                        'organizations_auto_followed_today', 'organizations_auto_followed_total',
                        'organizations_followed_today', 'organizations_followed_total',
                        'organizations_signed_in_total', 'organizations_with_linked_issues',
                        'organizations_with_new_positions_today', 'organizations_with_positions',
                        'visitors_today', 'visitors_total',
                        'voter_guide_entrants_today', 'voter_guides_viewed_today',
                        'voter_guides_viewed_total', 'welcome_page_entrants_today',
                    ])
                for one_dict in metrics_list_raw:
                    one_row = list(one_dict.values())
                    writer.writerow(one_row)

                return response
            else:
                analytics_action_list_json = []
                for one_dict in metrics_list_raw:
                    analytics_action_list_json.append(one_dict)
                return HttpResponse(json.dumps(analytics_action_list_json), content_type='application/json')
    except Exception as e:
        status += 'QUERY_FAILURE: ' + str(e) + ' '
        success = False

    status += 'SITEWIDE_DAILY_METRICS_LIST_EMPTY '
    json_data = {
        'success': success,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def sitewide_election_metrics_sync_out_view(request):  # sitewideElectionMetricsSyncOut
    status = ''
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'analytics_admin'}
    if not voter_has_authority(request, authority_required):
        json_data = {
            'success': False,
            'status': 'SITEWIDE_ELECTION_METRICS_SYNC_OUT-NOT_ANALYTICS_ADMIN '
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    starting_date_as_integer = convert_to_int(request.GET.get('starting_date_as_integer', 0))
    ending_date_as_integer = convert_to_int(request.GET.get('ending_date_as_integer', 0))
    return_csv_format = positive_value_exists(request.GET.get('return_csv_format', False))

    if not positive_value_exists(starting_date_as_integer):
        one_month_ago = now() - timedelta(days=30)
        starting_date_as_integer = convert_date_to_date_as_integer(one_month_ago)

    if not positive_value_exists(ending_date_as_integer):
        time_now = now()
        ending_date_as_integer = convert_date_to_date_as_integer(time_now)

    election_manager = ElectionManager()
    results = election_manager.retrieve_elections_between_dates(
        starting_date_as_integer=starting_date_as_integer,
        ending_date_as_integer=ending_date_as_integer
    )
    election_list = results['election_list']
    google_civic_election_id_list = []
    for one_election in election_list:
        google_civic_election_id_list.append(one_election.google_civic_election_id)

    try:
        metrics_query = SitewideElectionMetrics.objects.all().order_by('-id')
        metrics_query = metrics_query.filter(google_civic_election_id__in=google_civic_election_id_list)

        metrics_list_dict = metrics_query.values(
            'id', 'authenticated_visitors_total',
            'election_day_text', 'entered_full_address',
            'friends_only_positions', 'friends_only_positions_with_comments', 'google_civic_election_id',
            'individuals_with_friends_only_positions', 'individuals_with_positions',
            'individuals_with_public_positions',
            'issues_followed',
            'organization_public_positions', 'organizations_auto_followed', 'organizations_followed',
            'organizations_signed_in', 'organizations_with_positions',
            'public_positions', 'public_positions_with_comments',
            'unique_voters_that_auto_followed_organizations', 'unique_voters_that_followed_organizations',
            'visitors_total', 'voter_guide_entries',
            'voter_guide_views', 'voter_guides_viewed',
        )
        if metrics_list_dict:
            metrics_list_raw = list(metrics_list_dict)
            if return_csv_format:
                # Create the HttpResponse object with the appropriate CSV header.
                filename = "sitewideElectionMetricsSyncOut"
                filename += "-" + str(starting_date_as_integer)
                filename += "-" + str(ending_date_as_integer)
                filename += ".csv"
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="' + filename + '"'

                writer = csv.writer(response)
                writer.writerow(
                    [
                        'id', 'authenticated_visitors_total',
                        'election_day_text', 'entered_full_address',
                        'friends_only_positions', 'friends_only_positions_with_comments', 'google_civic_election_id',
                        'individuals_with_friends_only_positions', 'individuals_with_positions',
                        'individuals_with_public_positions',
                        'issues_followed',
                        'organization_public_positions', 'organizations_auto_followed', 'organizations_followed',
                        'organizations_signed_in', 'organizations_with_positions',
                        'public_positions', 'public_positions_with_comments',
                        'unique_voters_that_auto_followed_organizations', 'unique_voters_that_followed_organizations',
                        'visitors_total', 'voter_guide_entries',
                        'voter_guide_views', 'voter_guides_viewed',
                    ])
                for one_dict in metrics_list_raw:
                    one_row = list(one_dict.values())
                    writer.writerow(one_row)

                return response
            else:
                analytics_action_list_json = []
                for one_dict in metrics_list_raw:
                    analytics_action_list_json.append(one_dict)
                return HttpResponse(json.dumps(analytics_action_list_json), content_type='application/json')
    except Exception as e:
        status += 'QUERY_FAILURE: ' + str(e) + ' '
        success = False

    status += 'SITEWIDE_ELECTION_METRICS_LIST_EMPTY '
    json_data = {
        'success': success,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def sitewide_voter_metrics_sync_out_view(request):  # sitewideVoterMetricsSyncOut
    status = ''
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'analytics_admin'}
    if not voter_has_authority(request, authority_required):
        json_data = {
            'success': False,
            'status': 'SITEWIDE_VOTER_METRICS_SYNC_OUT-NOT_ANALYTICS_ADMIN '
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    starting_date_as_integer = convert_to_int(request.GET.get('starting_date_as_integer', 0))
    ending_date_as_integer = convert_to_int(request.GET.get('ending_date_as_integer', 0))
    return_csv_format = positive_value_exists(request.GET.get('return_csv_format', False))

    if positive_value_exists(starting_date_as_integer):
        starting_date = convert_date_as_integer_to_date(starting_date_as_integer)
    else:
        starting_date = now() - timedelta(days=30)
        starting_date_as_integer = convert_date_to_date_as_integer(starting_date)

    if positive_value_exists(ending_date_as_integer):
        ending_date = convert_date_as_integer_to_date(ending_date_as_integer)
    else:
        ending_date = now()
        ending_date_as_integer = convert_date_to_date_as_integer(ending_date)

    try:
        metrics_query = SitewideVoterMetrics.objects.all().order_by('-id')
        metrics_query = metrics_query.filter(last_action_date__gte=starting_date)
        metrics_query = metrics_query.filter(last_action_date__lte=ending_date)

        metrics_query = metrics_query.extra(
            select={'last_action_date': "to_char(last_action_date, 'YYYY-MM-DD HH24:MI:SS')"})
        metrics_list_dict = metrics_query.values(
            'id', 'actions_count', 'ballot_visited',
            'comments_entered_friends_only', 'comments_entered_public',
            'days_visited', 'elections_viewed',
            'entered_full_address', 'issues_followed',
            'last_action_date', 'last_calculated_date_as_integer',
            'organizations_followed', 'positions_entered_friends_only', 'positions_entered_public',
            'seconds_on_site', 'signed_in_facebook', 'signed_in_twitter', 'signed_in_with_email',
            'signed_in_with_sms_phone_number',
            'time_until_sign_in', 'voter_guides_viewed',
            'voter_we_vote_id', 'welcome_visited',
        )
        if metrics_list_dict:
            metrics_list_raw = list(metrics_list_dict)
            if return_csv_format:
                # Create the HttpResponse object with the appropriate CSV header.
                filename = "sitewideVoterMetricsSyncOut"
                filename += "-" + str(starting_date_as_integer)
                filename += "-" + str(ending_date_as_integer)
                filename += ".csv"
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="' + filename + '"'

                writer = csv.writer(response)
                writer.writerow(
                    [
                        'id', 'actions_count', 'ballot_visited',
                        'comments_entered_friends_only', 'comments_entered_public',
                        'days_visited', 'elections_viewed',
                        'entered_full_address', 'issues_followed',
                        'last_action_date', 'last_calculated_date_as_integer',
                        'organizations_followed', 'positions_entered_friends_only', 'positions_entered_public',
                        'seconds_on_site', 'signed_in_facebook', 'signed_in_twitter', 'signed_in_with_email',
                        'signed_in_with_sms_phone_number',
                        'time_until_sign_in', 'voter_guides_viewed',
                        'voter_we_vote_id', 'welcome_visited',
                    ])
                for one_dict in metrics_list_raw:
                    one_row = list(one_dict.values())
                    writer.writerow(one_row)

                return response
            else:
                analytics_action_list_json = []
                for one_dict in metrics_list_raw:
                    analytics_action_list_json.append(one_dict)
                return HttpResponse(json.dumps(analytics_action_list_json), content_type='application/json')
    except Exception as e:
        status += 'QUERY_FAILURE: ' + str(e) + ' '
        success = False

    status += 'SITEWIDE_VOTER_METRICS_LIST_EMPTY '
    json_data = {
        'success': success,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def analytics_index_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)
    voter_allowed_to_see_organization_analytics = True

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    date_to_process = convert_to_int(request.GET.get('date_to_process', 0))
    analytics_date_as_integer_last_processed = \
        convert_to_int(request.GET.get('analytics_date_as_integer_last_processed', 0))

    sitewide_election_metrics_list = []
    try:
        sitewide_election_metrics_query = SitewideElectionMetrics.objects.using('analytics')\
            .order_by('-election_day_text')
        sitewide_election_metrics_query = sitewide_election_metrics_query[:3]
        sitewide_election_metrics_list = list(sitewide_election_metrics_query)
    except SitewideElectionMetrics.DoesNotExist:
        # This is fine
        pass

    sitewide_daily_metrics_list_modified = []
    try:
        sitewide_daily_metrics_query = SitewideDailyMetrics.objects.using('analytics').order_by('-date_as_integer')
        sitewide_daily_metrics_query = sitewide_daily_metrics_query[:3]
        sitewide_daily_metrics_list = list(sitewide_daily_metrics_query)
        for one_day in sitewide_daily_metrics_list:
            if positive_value_exists(one_day.authenticated_visitors_today) and \
                    positive_value_exists(one_day.visitors_today):
                visitors_ratio = one_day.authenticated_visitors_today / one_day.visitors_today
                percent_raw = visitors_ratio * 100
                one_day.authenticated_visitors_percent_of_all_today = "{:.2f}".format(percent_raw)
            sitewide_daily_metrics_list_modified.append(one_day)
    except SitewideDailyMetrics.DoesNotExist:
        # This is fine
        pass

    organization_election_metrics_list = []
    try:
        organization_election_metrics_query = OrganizationElectionMetrics.objects.using('analytics').\
            order_by('-followers_visited_ballot')
        organization_election_metrics_query = organization_election_metrics_query[:3]
        organization_election_metrics_list = list(organization_election_metrics_query)
    except OrganizationElectionMetrics.DoesNotExist:
        # This is fine
        pass

    sitewide_voter_metrics_list = []
    try:
        sitewide_voter_metrics_query = SitewideVoterMetrics.objects.using('analytics').order_by('-last_action_date')
        # Don't return the welcome page bounces
        sitewide_voter_metrics_query = sitewide_voter_metrics_query.exclude(welcome_visited=1, actions_count=1)
        sitewide_voter_metrics_query = sitewide_voter_metrics_query.exclude(actions_count__lte=1)
        sitewide_voter_metrics_query = sitewide_voter_metrics_query[:3]
        sitewide_voter_metrics_list = list(sitewide_voter_metrics_query)
    except SitewideVoterMetrics.DoesNotExist:
        # This is fine
        pass

    election_list = Election.objects.order_by('-election_day_text')

    we_vote_settings_manager = WeVoteSettingsManager()
    results = we_vote_settings_manager.fetch_setting_results('analytics_date_as_integer_last_processed')
    if results['we_vote_setting_found']:
        analytics_date_as_integer_last_processed = convert_to_int(results['setting_value'])

    analytics_date_last_processed = None
    if positive_value_exists(analytics_date_as_integer_last_processed):
        analytics_date_last_processed = convert_date_as_integer_to_date(analytics_date_as_integer_last_processed)

    messages_on_stage = get_messages(request)

    template_values = {
        'analytics_date_as_integer_last_processed':     analytics_date_as_integer_last_processed,
        'analytics_date_last_processed':                analytics_date_last_processed,
        'messages_on_stage':                            messages_on_stage,
        'WEB_APP_ROOT_URL':                             WEB_APP_ROOT_URL,
        'sitewide_election_metrics_list':               sitewide_election_metrics_list,
        'sitewide_daily_metrics_list':                  sitewide_daily_metrics_list_modified,
        'sitewide_voter_metrics_list':                  sitewide_voter_metrics_list,
        'organization_election_metrics_list':           organization_election_metrics_list,
        'voter_allowed_to_see_organization_analytics':  voter_allowed_to_see_organization_analytics,
        'state_code':                                   state_code,
        'google_civic_election_id':                     google_civic_election_id,
        'election_list':                                election_list,
        'date_to_process':                              date_to_process,
    }
    return render(request, 'analytics/index.html', template_values)


@login_required
def analytics_index_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    analytics_date_as_integer_last_processed = \
        convert_to_int(request.GET.get('analytics_date_as_integer_last_processed', 0))

    we_vote_settings_manager = WeVoteSettingsManager()
    if positive_value_exists(analytics_date_as_integer_last_processed):
        # Update this value in the settings table: analytics_date_as_integer_last_processed
        # ...to new_analytics_date_as_integer
        results = we_vote_settings_manager.save_setting(
            setting_name="analytics_date_as_integer_last_processed",
            setting_value=analytics_date_as_integer_last_processed,
            value_type=WeVoteSetting.INTEGER)
        messages.add_message(request, messages.INFO, 'Analytics processing date updated.')
    return HttpResponseRedirect(reverse('analytics:analytics_index', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def organization_analytics_index_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')

    organization_election_metrics_list = []
    try:
        organization_election_metrics_query = OrganizationElectionMetrics.objects.using('analytics').\
            order_by('-election_day_text')
        organization_election_metrics_query = \
            organization_election_metrics_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
        organization_election_metrics_query = organization_election_metrics_query[:3]
        organization_election_metrics_list = list(organization_election_metrics_query)
    except OrganizationElectionMetrics.DoesNotExist:
        # This is fine
        pass

    organization_daily_metrics_list = []
    try:
        organization_daily_metrics_query = \
            OrganizationDailyMetrics.objects.using('analytics').order_by('-date_as_integer')
        organization_daily_metrics_query = \
            organization_daily_metrics_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
        organization_daily_metrics_query = organization_daily_metrics_query[:3]
        organization_daily_metrics_list = list(organization_daily_metrics_query)
    except OrganizationDailyMetrics.DoesNotExist:
        # This is fine
        pass

    messages_on_stage = get_messages(request)

    voter_allowed_to_see_organization_analytics = False  # To be implemented
    template_values = {
        'messages_on_stage':                            messages_on_stage,
        'organization_election_metrics_list':           organization_election_metrics_list,
        'organization_daily_metrics_list':              organization_daily_metrics_list,
        'voter_allowed_to_see_organization_analytics':  voter_allowed_to_see_organization_analytics,
        'state_code':                                   state_code,
        'google_civic_election_id':                     google_civic_election_id,
        'organization_we_vote_id':                      organization_we_vote_id,
    }
    return render(request, 'analytics/organization_analytics_index.html', template_values)


@login_required
def organization_daily_metrics_process_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    state_code = request.GET.get('state_code', '')
    changes_since_this_date_as_integer = convert_to_int(request.GET.get('date_as_integer', 0))
    through_date_as_integer = convert_to_int(request.GET.get('through_date_as_integer', 0))

    if not positive_value_exists(changes_since_this_date_as_integer):
        messages.add_message(request, messages.ERROR, 'date_as_integer required.')
        return HttpResponseRedirect(reverse('analytics:organization_daily_metrics', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    results = save_organization_daily_metrics(organization_we_vote_id, changes_since_this_date_as_integer)

    return HttpResponseRedirect(reverse('analytics:organization_daily_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code) +
                                "&date_as_integer=" + str(changes_since_this_date_as_integer) +
                                "&through_date_as_integer=" + str(through_date_as_integer)
                                )


@login_required
def analytics_action_list_view(request, voter_we_vote_id=False, organization_we_vote_id=False, incorrect_integer=0):
    """

    :param request:
    :param voter_we_vote_id:
    :param organization_we_vote_id:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    analytics_action_search = request.GET.get('analytics_action_search', '')
    show_user_agent = request.GET.get('show_user_agent', '')

    date_as_integer = convert_to_int(request.GET.get('date_as_integer', 0))
    through_date_as_integer = convert_to_int(request.GET.get('through_date_as_integer', date_as_integer))
    start_date = None
    if positive_value_exists(date_as_integer):
        start_date = convert_date_as_integer_to_date(date_as_integer)
    through_date = None
    if positive_value_exists(through_date_as_integer):
        through_date_as_integer_modified = through_date_as_integer + 1
        try:
            through_date = convert_date_as_integer_to_date(through_date_as_integer_modified)
        except Exception as e:
            through_date = convert_date_as_integer_to_date(through_date_as_integer)

    analytics_action_list = []

    messages_on_stage = get_messages(request)
    try:
        analytics_action_query = AnalyticsAction.objects.using('analytics').order_by('-id')
        if positive_value_exists(date_as_integer):
            analytics_action_query = analytics_action_query.filter(date_as_integer__gte=date_as_integer)
        if positive_value_exists(through_date_as_integer):
            analytics_action_query = analytics_action_query.filter(
                date_as_integer__lte=through_date_as_integer)
        if positive_value_exists(voter_we_vote_id):
            analytics_action_query = analytics_action_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
        if positive_value_exists(google_civic_election_id):
            analytics_action_query = analytics_action_query.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(organization_we_vote_id):
            analytics_action_query = analytics_action_query.filter(
                organization_we_vote_id__iexact=organization_we_vote_id)

        if positive_value_exists(analytics_action_search):
            search_words = analytics_action_search.split()
            for one_word in search_words:
                one_word_integer = convert_to_int(one_word)
                action_constant_integer = fetch_action_constant_number_from_constant_string(one_word)

                filters = []

                if positive_value_exists(action_constant_integer):
                    new_filter = Q(action_constant=action_constant_integer)
                    filters.append(new_filter)

                new_filter = Q(ballot_item_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                if positive_value_exists(one_word_integer):
                    new_filter = Q(date_as_integer=one_word_integer)
                    filters.append(new_filter)

                if positive_value_exists(one_word_integer):
                    new_filter = Q(google_civic_election_id=one_word_integer)
                    filters.append(new_filter)

                if positive_value_exists(one_word_integer):
                    new_filter = Q(id=one_word_integer)
                    filters.append(new_filter)

                new_filter = Q(organization_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(state_code__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(voter_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    analytics_action_query = analytics_action_query.filter(final_filters)

        if positive_value_exists(voter_we_vote_id) or positive_value_exists(organization_we_vote_id) \
                or positive_value_exists(date_as_integer) or positive_value_exists(through_date_as_integer):
            analytics_action_query = analytics_action_query[:500]
        else:
            analytics_action_query = analytics_action_query[:200]
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
        'show_user_agent':          show_user_agent,
        'date_as_integer':          date_as_integer,
        'start_date':               start_date,
        'through_date_as_integer':  through_date_as_integer,
        'through_date':             through_date,
    }
    return render(request, 'analytics/analytics_action_list.html', template_values)


@login_required
def augment_voter_analytics_process_view(request, voter_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    changes_since_this_date_as_integer = convert_to_int(request.GET.get('date_as_integer', 0))

    analytics_manager = AnalyticsManager()
    first_visit_today_results = analytics_manager.update_first_visit_today_for_one_voter(voter_we_vote_id)

    results = augment_one_voter_analytics_action_entries_without_election_id(voter_we_vote_id)

    messages.add_message(request, messages.INFO,
                         str(results['analytics_updated_count']) + ' analytics entries updated.<br />')

    return HttpResponseRedirect(reverse('analytics:analytics_action_list', args=(voter_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code) +
                                "&date_as_integer=" + str(changes_since_this_date_as_integer)
                                )


@login_required
def organization_daily_metrics_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')

    organization_daily_metrics_list = []

    messages_on_stage = get_messages(request)
    try:
        organization_daily_metrics_query = OrganizationDailyMetrics.objects.using('analytics').\
            order_by('-date_as_integer')
        organization_daily_metrics_query = organization_daily_metrics_query.filter(
            organization_we_vote_id__iexact=organization_we_vote_id)
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
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'google_civic_election_id required.')
        return HttpResponseRedirect(reverse('analytics:organization_election_metrics', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code)
                                    )

    analytics_manager = AnalyticsManager()
    if positive_value_exists(organization_we_vote_id):
        one_organization_results = save_organization_election_metrics(google_civic_election_id, organization_we_vote_id)
        messages.add_message(request, messages.INFO, one_organization_results['status'])
    else:
        results = analytics_manager.retrieve_organization_list_with_election_activity(google_civic_election_id)
        if results['organization_we_vote_id_list_found']:
            organization_we_vote_id_list = results['organization_we_vote_id_list']
            for organization_we_vote_id in organization_we_vote_id_list:
                save_organization_election_metrics(google_civic_election_id, organization_we_vote_id)

    return HttpResponseRedirect(reverse('analytics:organization_election_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code)
                                )


@login_required
def organization_election_metrics_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')

    organization_election_metrics_list = []
    try:
        organization_election_metrics_query = OrganizationElectionMetrics.objects.using('analytics').\
            order_by('-followers_visited_ballot')
        if positive_value_exists(google_civic_election_id):
            organization_election_metrics_query = \
                organization_election_metrics_query.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(organization_we_vote_id):
            organization_election_metrics_query = \
                organization_election_metrics_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
        organization_election_metrics_list = list(organization_election_metrics_query)
    except OrganizationElectionMetrics.DoesNotExist:
        # This is fine
        pass

    election_list = Election.objects.order_by('-election_day_text')

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'WEB_APP_ROOT_URL':                     WEB_APP_ROOT_URL,
        'organization_election_metrics_list':   organization_election_metrics_list,
        'google_civic_election_id':             google_civic_election_id,
        'organization_we_vote_id':              organization_we_vote_id,
        'election_list':                        election_list,
        'state_code':                           state_code,
    }
    return render(request, 'analytics/organization_election_metrics.html', template_values)


@login_required
def sitewide_daily_metrics_process_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    changes_since_this_date_as_integer = convert_to_int(request.GET.get('date_as_integer', 0))
    through_date_as_integer = convert_to_int(request.GET.get('through_date_as_integer',
                                                             changes_since_this_date_as_integer))

    # analytics_manager = AnalyticsManager()
    # first_visit_today_results = \
    #     analytics_manager.update_first_visit_today_for_all_voters_since_date(
    #         changes_since_this_date_as_integer, through_date_as_integer)
    #
    # augment_results = augment_voter_analytics_action_entries_without_election_id(
    #     changes_since_this_date_as_integer, through_date_as_integer)

    results = save_sitewide_daily_metrics(changes_since_this_date_as_integer, through_date_as_integer)

    # messages.add_message(
    #     request, messages.INFO,
    #     str(first_visit_today_results['first_visit_today_count']) + ' first visit updates.<br />' +
    #     'augment-analytics_updated_count: ' + str(augment_results['analytics_updated_count']) + '<br />' +
    #     'sitewide_daily_metrics_saved_count: ' + str(results['sitewide_daily_metrics_saved_count']) + '')
    messages.add_message(
        request, messages.INFO,
        'sitewide_daily_metrics_saved_count: ' + str(results['sitewide_daily_metrics_saved_count']) + '')

    return HttpResponseRedirect(reverse('analytics:sitewide_daily_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code) +
                                "&date_as_integer=" + str(changes_since_this_date_as_integer) +
                                "&through_date_as_integer=" + str(through_date_as_integer)
                                )


@login_required
def sitewide_daily_metrics_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    date_as_integer = convert_to_int(request.GET.get('date_as_integer', 0))
    through_date_as_integer = convert_to_int(request.GET.get('through_date_as_integer', date_as_integer))

    start_date = None
    if positive_value_exists(date_as_integer):
        start_date = convert_date_as_integer_to_date(date_as_integer)
    through_date = None
    if positive_value_exists(through_date_as_integer):
        through_date_as_integer_modified = through_date_as_integer + 1
        through_date = convert_date_as_integer_to_date(through_date_as_integer_modified)

    sitewide_daily_metrics_list_modified = []

    messages_on_stage = get_messages(request)
    try:
        sitewide_daily_metrics_query = SitewideDailyMetrics.objects.using('analytics').order_by('-date_as_integer')
        if positive_value_exists(date_as_integer):
            sitewide_daily_metrics_query = sitewide_daily_metrics_query.filter(date_as_integer__gte=date_as_integer)
        if positive_value_exists(through_date_as_integer):
            sitewide_daily_metrics_query = sitewide_daily_metrics_query.filter(
                date_as_integer__lte=through_date_as_integer)
        sitewide_daily_metrics_list = sitewide_daily_metrics_query[:180]  # Limit to no more than 6 months
        for one_day in sitewide_daily_metrics_list:
            if positive_value_exists(one_day.authenticated_visitors_today) and \
                    positive_value_exists(one_day.visitors_today):
                visitors_ratio = one_day.authenticated_visitors_today / one_day.visitors_today
                percent_raw = visitors_ratio * 100
                one_day.authenticated_visitors_percent_of_all_today = "{:.2f}".format(percent_raw)
            sitewide_daily_metrics_list_modified.append(one_day)
    except SitewideDailyMetrics.DoesNotExist:
        # This is fine
        pass

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'sitewide_daily_metrics_list':  sitewide_daily_metrics_list_modified,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
        'date_as_integer':              date_as_integer,
        'through_date_as_integer':      through_date_as_integer,
        'start_date':                   start_date,
        'through_date':                 through_date,
    }
    return render(request, 'analytics/sitewide_daily_metrics.html', template_values)


@login_required
def sitewide_election_metrics_process_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'google_civic_election_id required.')
        return HttpResponseRedirect(reverse('analytics:sitewide_election_metrics', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    results = save_sitewide_election_metrics(google_civic_election_id)  # DEBUG=1
    messages.add_message(request, messages.INFO,
                         ' NEED TO UPGRADE TO INCLUDE NATIONAL ELECTION TO INCLUDE STATE')

    return HttpResponseRedirect(reverse('analytics:sitewide_election_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def sitewide_election_metrics_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    sitewide_election_metrics_list = []

    try:
        sitewide_election_metrics_query = SitewideElectionMetrics.objects.using('analytics').\
            order_by('-election_day_text')
        sitewide_election_metrics_list = list(sitewide_election_metrics_query)
    except SitewideElectionMetrics.DoesNotExist:
        # This is fine
        pass

    election_list = Election.objects.order_by('-election_day_text')

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'sitewide_election_metrics_list':   sitewide_election_metrics_list,
        'google_civic_election_id':         google_civic_election_id,
        'state_code':                       state_code,
        'election_list':                    election_list,
    }
    return render(request, 'analytics/sitewide_election_metrics.html', template_values)


@login_required
def sitewide_voter_metrics_process_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    augment_voter_data = request.GET.get('augment_voter_data', '')
    erase_existing_voter_metrics_data = request.GET.get('erase_existing_voter_metrics_data', False)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    changes_since_this_date_as_integer = convert_to_int(request.GET.get('date_as_integer', 0))
    through_date_as_integer = convert_to_int(request.GET.get('through_date_as_integer',
                                                             changes_since_this_date_as_integer))

    first_visit_today_count = 0
    sitewide_voter_metrics_updated = 0
    if positive_value_exists(augment_voter_data):
        message = "[sitewide_voter_metrics_process_view, start: " + str(changes_since_this_date_as_integer) + "" \
                  ", end: " + str(through_date_as_integer) + ", " \
                  "STARTING update_first_visit_today_for_all_voters_since_date]"
        print_to_log(logger=logger, exception_message_optional=message)

        analytics_manager = AnalyticsManager()
        first_visit_today_results = analytics_manager.update_first_visit_today_for_all_voters_since_date(
                changes_since_this_date_as_integer, through_date_as_integer)
        first_visit_today_count = first_visit_today_results['first_visit_today_count']

        message = "[sitewide_voter_metrics_process_view, STARTING " \
                  "augment_voter_analytics_action_entries_without_election_id]"
        print_to_log(logger=logger, exception_message_optional=message)

        results = augment_voter_analytics_action_entries_without_election_id(
            changes_since_this_date_as_integer, through_date_as_integer)

    if positive_value_exists(erase_existing_voter_metrics_data):
        # Add code here to erase data for all of the voters who otherwise would be updated between
        #  the dates: changes_since_this_date_as_integer and through_date_as_integer
        pass
    else:
        message = "[sitewide_voter_metrics_process_view, STARTING " \
                  "save_sitewide_voter_metrics]"
        print_to_log(logger=logger, exception_message_optional=message)
        results = save_sitewide_voter_metrics(changes_since_this_date_as_integer, through_date_as_integer)
        sitewide_voter_metrics_updated = results['sitewide_voter_metrics_updated']

        message = "[sitewide_voter_metrics_process_view, FINISHED " \
                  "save_sitewide_voter_metrics]"
        print_to_log(logger=logger, exception_message_optional=message)

    messages.add_message(request, messages.INFO,
                         str(first_visit_today_count) + ' first visit updates.<br />' +
                         'voters with updated metrics: ' + str(sitewide_voter_metrics_updated) + '')

    return HttpResponseRedirect(reverse('analytics:sitewide_voter_metrics', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code) +
                                "&augment_voter_data=" + str(augment_voter_data) +
                                "&date_as_integer=" + str(changes_since_this_date_as_integer) +
                                "&through_date_as_integer=" + str(through_date_as_integer)
                                )


@login_required
def sitewide_voter_metrics_view(request):
    """
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    date_as_integer = convert_to_int(request.GET.get('date_as_integer', 0))
    through_date_as_integer = convert_to_int(request.GET.get('through_date_as_integer', date_as_integer))

    start_date = None
    if positive_value_exists(date_as_integer):
        start_date = convert_date_as_integer_to_date(date_as_integer)
    through_date = None
    if positive_value_exists(through_date_as_integer):
        through_date_as_integer_modified = through_date_as_integer + 1
        through_date = convert_date_as_integer_to_date(through_date_as_integer_modified)

    sitewide_voter_metrics_list_short = []

    try:
        sitewide_voter_metrics_query = SitewideVoterMetrics.objects.using('analytics').order_by('-last_action_date')
        sitewide_voter_metrics_query = sitewide_voter_metrics_query.exclude(actions_count__lte=1)
        if positive_value_exists(date_as_integer):
            sitewide_voter_metrics_query = sitewide_voter_metrics_query.filter(last_action_date__gte=start_date)
        if positive_value_exists(through_date_as_integer):
            sitewide_voter_metrics_query = sitewide_voter_metrics_query.filter(
                last_action_date__lte=through_date)
        sitewide_voter_metrics_list = list(sitewide_voter_metrics_query)

        # Count how many bounces are being removed
        bounce_query = SitewideVoterMetrics.objects.using('analytics').all()
        bounce_query = bounce_query.filter(actions_count__lte=1)
        if positive_value_exists(date_as_integer):
            bounce_query = bounce_query.filter(last_action_date__gte=start_date)
        if positive_value_exists(through_date_as_integer):
            bounce_query = bounce_query.filter(last_action_date__lte=through_date)
        bounce_count = bounce_query.count()

        # And the total we found
        total_number_of_voters_without_bounce = len(sitewide_voter_metrics_list)

        number_of_voters_to_show = 400
        sitewide_voter_metrics_list_short = sitewide_voter_metrics_list[:number_of_voters_to_show]

        # Bounce rate
        total_voters = total_number_of_voters_without_bounce + bounce_count
        if positive_value_exists(bounce_count) and positive_value_exists(total_voters):
            voter_bounce_rate = bounce_count / total_voters
            percent_raw = voter_bounce_rate * 100
            voter_bounce_rate = "{:.2f}".format(percent_raw)
        else:
            voter_bounce_rate = 0

        messages.add_message(request, messages.INFO,
                             format(total_number_of_voters_without_bounce, ",") + ' voters with activity. ' +
                             str(voter_bounce_rate) +
                             '% visitors who left with only one view (bounced without activity).')

    except SitewideVoterMetrics.DoesNotExist:
        # This is fine
        pass

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'sitewide_voter_metrics_list':  sitewide_voter_metrics_list_short,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
        'date_as_integer':              date_as_integer,
        'start_date':                   start_date,
        'through_date_as_integer':      through_date_as_integer,
        'through_date':                 through_date,
    }
    return render(request, 'analytics/sitewide_voter_metrics.html', template_values)
