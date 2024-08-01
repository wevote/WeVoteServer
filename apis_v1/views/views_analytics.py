# apis_v1/views/views_analytics.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from analytics.controllers import save_analytics_action_for_api
from analytics.models import ACTION_BALLOT_VISIT, ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS, AnalyticsAction
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from organization.models import OrganizationManager
import robot_detection
from django_user_agents.utils import get_user_agent
from voter.models import Voter, VoterDeviceLinkManager, voter_has_authority, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, is_voter_device_id_valid, \
    positive_value_exists, STATE_CODE_MAP

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def voter_aggregate_analytics_view(request):  # voterAggregateAnalytics
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_county_topics = positive_value_exists(request.GET.get('show_county_topics', 0))
    show_counties = show_county_topics or positive_value_exists(request.GET.get('show_county_topics', 0))
    show_counties_without_activity = positive_value_exists(request.GET.get('show_counties_without_activity', 0))
    show_state_topics = positive_value_exists(request.GET.get('show_state_topics', 0))
    show_states_without_activity = positive_value_exists(request.GET.get('show_states_without_activity', 0))
    show_this_year_of_analytics = convert_to_int(request.GET.get('show_this_year_of_analytics', 0))
    status = ''
    success = True
    analytics_action_code_list = [ACTION_BALLOT_VISIT]

    analytics_queryset = AnalyticsAction.objects.using('readonly').all()
    analytics_queryset = analytics_queryset.filter(action_constant__in=analytics_action_code_list)
    if positive_value_exists(google_civic_election_id):
        analytics_queryset = analytics_queryset.filter(google_civic_election_id=google_civic_election_id)
    if positive_value_exists(show_this_year_of_analytics):
        first_day_of_year = convert_to_int("{year}0101".format(year=show_this_year_of_analytics))
        last_day_of_year = convert_to_int("{year}1231".format(year=show_this_year_of_analytics))
        analytics_queryset = analytics_queryset.filter(date_as_integer__gte=first_day_of_year)
        analytics_queryset = analytics_queryset.filter(date_as_integer__lte=last_day_of_year)
    analytics_queryset = analytics_queryset.values_list('voter_we_vote_id', flat=True).distinct()
    voter_count = analytics_queryset.count()
    voter_we_vote_id_list_for_country = list(analytics_queryset)

    from voter.models import VoterIssuesLookup
    issues_queryset = VoterIssuesLookup.objects.using('readonly').all()
    issues_queryset = issues_queryset.filter(voter_we_vote_id__in=voter_we_vote_id_list_for_country)
    country_voters_following_topics = issues_queryset.count()

    likely_democrat_query = issues_queryset.filter(likely_democrat_from_issues=True)
    likely_democrat_from_issues = likely_democrat_query.count()
    likely_green_query = issues_queryset.filter(likely_green_from_issues=True)
    likely_green_from_issues = likely_green_query.count()
    likely_left_query = issues_queryset.filter(likely_left_from_issues=True)
    likely_left_from_issues = likely_left_query.count()
    likely_libertarian_query = issues_queryset.filter(likely_libertarian_from_issues=True)
    likely_libertarian_from_issues = likely_libertarian_query.count()
    likely_republican_query = issues_queryset.filter(likely_republican_from_issues=True)
    likely_republican_from_issues = likely_republican_query.count()
    likely_right_query = issues_queryset.filter(likely_right_from_issues=True)
    likely_right_from_issues = likely_right_query.count()

    all_states_dict = {}
    if show_county_topics or show_state_topics:
        from issue.models import ACTIVE_ISSUES_DICTIONARY, VOTER_ISSUES_LOOKUP_DICT
        issues_dictionary = ACTIVE_ISSUES_DICTIONARY
        voter_issues_lookup_dict = VOTER_ISSUES_LOOKUP_DICT
    else:
        issues_dictionary = {}
        voter_issues_lookup_dict = {}
    if positive_value_exists(show_counties) or show_counties_without_activity:
        from analytics.constants_fips_codes import COUNTIES_BY_STATE
        counties_by_state_dict = COUNTIES_BY_STATE
    else:
        counties_by_state_dict = {}
    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())
    voter_queryset = Voter.objects.using('readonly').all()
    for state_code, state_name in sorted_state_list:
        analytics_queryset_state = analytics_queryset.filter(state_code__iexact=state_code)
        voters_in_state_count = analytics_queryset_state.count()
        voter_we_vote_id_list_for_state = list(analytics_queryset_state)
        voters_in_state_following_topics = 0
        topics_by_state = []
        topics_by_state_ordered = []
        if positive_value_exists(show_state_topics) and positive_value_exists(voters_in_state_count):
            issues_queryset = VoterIssuesLookup.objects.using('readonly').all()
            issues_queryset = issues_queryset.filter(voter_we_vote_id__in=voter_we_vote_id_list_for_state)
            voters_in_state_following_topics = issues_queryset.count()

            # Statewide topics loop here
            for key, item in issues_dictionary.items():
                issue_we_vote_id = key
                topic_name = item
                voter_issues_lookup_name = voter_issues_lookup_dict.get(issue_we_vote_id)
                issues_queryset_one_topic = issues_queryset.filter(**{voter_issues_lookup_name: True})
                voters_in_state_following_this_topic = issues_queryset_one_topic.count()
                if positive_value_exists(voters_in_state_following_this_topic):
                    percent_voters_in_state_following = \
                        round((float(voters_in_state_following_this_topic / voters_in_state_count) * 100), 2)
                    percent_voters_in_state_following_active_only_float = \
                        round((float(voters_in_state_following_this_topic / voters_in_state_following_topics) * 100), 2)
                    state_topic_dict = {
                        'topic_name': topic_name,
                        'issue_we_vote_id': issue_we_vote_id,
                        'voters_in_state_following_this_topic': voters_in_state_following_this_topic,
                        'percent_voters_in_state_following': "{percent}%".format(
                            percent=percent_voters_in_state_following),
                        'percent_voters_in_state_following_active_only': "{percent}%".format(
                            percent=percent_voters_in_state_following_active_only_float),
                    }
                    topics_by_state.append(state_topic_dict)
            for state_topic_dict in (sorted(topics_by_state,
                                            key=lambda x: x['voters_in_state_following_this_topic'],
                                            reverse=True)):
                topics_by_state_ordered.append(state_topic_dict)
        counties_list = []
        if positive_value_exists(show_counties) and positive_value_exists(voters_in_state_count) \
                or show_counties_without_activity:
            # We do not search directly in the Voter table for state, because the voter may have moved
            #  since the analytics entry was created.
            voter_queryset_this_state = voter_queryset.filter(we_vote_id__in=voter_we_vote_id_list_for_state)
            # Counties loop here
            if state_code not in counties_by_state_dict:
                # This can happen with state_code == 'NA'
                continue
            for county in counties_by_state_dict[state_code]:
                if 'county_fips_code' not in county:
                    continue
                county_fips_code = county['county_fips_code']
                if not positive_value_exists(county_fips_code):
                    continue
                voter_queryset_this_county = voter_queryset_this_state.filter(county_fips_code=county_fips_code)
                voters_in_county = voter_queryset_this_county.count()
                voter_queryset_this_county = voter_queryset_this_county.values_list('we_vote_id', flat=True).distinct()
                voter_we_vote_id_list_this_county = list(voter_queryset_this_county)
                county_dict = {
                    'county_name': county['county_name'],
                    'county_short_name': county['county_short_name'],
                    'county_fips_code': county_fips_code,
                    'voters_in_county': voters_in_county,
                }
                if positive_value_exists(show_county_topics) and positive_value_exists(voters_in_county):
                    topics_for_one_county = []
                    topics_for_one_county_ordered = []
                    county_issues_queryset = VoterIssuesLookup.objects.using('readonly').all()
                    county_issues_queryset = county_issues_queryset.filter(
                        voter_we_vote_id__in=voter_we_vote_id_list_this_county)
                    voters_in_county_following_topics = county_issues_queryset.count()
                    county_dict['voters_in_county_following_topics'] = voters_in_county_following_topics
                    percent_voters_in_county_following_topics_float = \
                        round(
                            (float(voters_in_county_following_topics /
                                   voters_in_county) * 100), 2)
                    county_dict['percent_voters_in_county_following_topics'] = "{percent}%".format(
                                        percent=percent_voters_in_county_following_topics_float)

                    if positive_value_exists(voters_in_county_following_topics):
                        # County topics loop here
                        for key, item in issues_dictionary.items():
                            issue_we_vote_id = key
                            topic_name = item
                            voter_issues_lookup_name = voter_issues_lookup_dict.get(issue_we_vote_id)
                            issues_queryset_one_topic = county_issues_queryset.filter(**{voter_issues_lookup_name: True})
                            voters_in_county_following_this_topic = issues_queryset_one_topic.count()
                            if positive_value_exists(voters_in_county_following_this_topic):
                                percent_voters_in_county_following_this_topic = \
                                    round((float(voters_in_county_following_this_topic / voters_in_county) * 100), 2)
                                percent_voters_in_county_following_this_topic_active_only_float = \
                                    round(
                                        (float(voters_in_county_following_this_topic /
                                               voters_in_county_following_topics) * 100), 2)
                                county_topic_dict = {
                                    'topic_name': topic_name,
                                    'issue_we_vote_id': issue_we_vote_id,
                                    'voters_in_county_following_this_topic': voters_in_county_following_this_topic,
                                    'percent_voters_in_county_following': "{percent}%".format(
                                        percent=percent_voters_in_county_following_this_topic),
                                    'percent_voters_in_county_following_active_only': "{percent}%".format(
                                        percent=percent_voters_in_county_following_this_topic_active_only_float),
                                }
                                topics_for_one_county.append(county_topic_dict)

                    for county_topic_dict in (sorted(topics_for_one_county,
                                                     key=lambda x: x['voters_in_county_following_this_topic'],
                                                     reverse=True)):
                        topics_for_one_county_ordered.append(county_topic_dict)
                    county_dict['topics_for_one_county'] = topics_for_one_county_ordered
                if positive_value_exists(voters_in_county) or show_counties_without_activity:
                    # Only add to list if there are voters in this county
                    counties_list.append(county_dict)

        one_state_dict = {
            'state_name': state_name,
            'voters_in_state': voters_in_state_count,
        }
        if positive_value_exists(show_state_topics):
            one_state_dict['voters_in_state_following_topics'] = voters_in_state_following_topics
            if voters_in_state_count:
                percent_voters_in_state_following_topics_float = \
                    round((float(voters_in_state_following_topics / voters_in_state_count) * 100), 2)
            else:
                percent_voters_in_state_following_topics_float = 0.0
            one_state_dict['percent_voters_in_state_following_topics'] = \
                "{percent}%".format(percent=percent_voters_in_state_following_topics_float)
            one_state_dict['topics_by_state'] = topics_by_state_ordered
        if positive_value_exists(show_counties) or show_counties_without_activity:
            one_state_dict['counties'] = counties_list
        if positive_value_exists(voters_in_state_count) or show_states_without_activity:
            all_states_dict[state_code] = one_state_dict

    json_data = {
        'status':                   status,
        'success':                  success,
        'documentation_url':        "https://api.wevoteusa.org/apis/v1/docs/voterAggregateAnalytics/",
        'query_builder_url':        "https://api.wevoteusa.org/a/query_builder/",
        'google_civic_election_id': google_civic_election_id,
        'voters':                   voter_count,
    }
    json_data['voters_following_topics'] = country_voters_following_topics
    percent_voters_following_topics_float = round((float(country_voters_following_topics / voter_count) * 100), 2)
    json_data['percent_voters_following_topics'] = "{percent}%".format(percent=percent_voters_following_topics_float)
    json_data['year'] = show_this_year_of_analytics
    json_data['likely_left_from_issues'] = likely_left_from_issues
    json_data['likely_right_from_issues'] = likely_right_from_issues
    json_data['likely_democrat_from_issues'] = likely_democrat_from_issues
    json_data['likely_green_from_issues'] = likely_green_from_issues
    json_data['likely_libertarian_from_issues'] = likely_libertarian_from_issues
    json_data['likely_republican_from_issues'] = likely_republican_from_issues
    json_data['show_states_without_activity'] = show_states_without_activity
    json_data['show_state_topics'] = show_state_topics
    json_data['show_counties'] = show_counties
    json_data['show_counties_without_activity'] = show_counties_without_activity
    json_data['show_county_topics'] = show_county_topics
    json_data['states'] = all_states_dict
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_list_analytics_view(request):  # voterListAnalytics
    show_signed_in_voters = positive_value_exists(request.GET.get('show_signed_in_voters', False))
    show_we_vote_id_only = positive_value_exists(request.GET.get('show_we_vote_id_only', False))
    voter_count_requested_default = 10000
    voter_count_requested = convert_to_int(request.GET.get('voter_count_requested', voter_count_requested_default))
    if not positive_value_exists(voter_count_requested):
        voter_count_requested = voter_count_requested_default
    voter_count_returned = 0
    voter_count_total = 0
    voter_index_end = 0
    voter_index_start = convert_to_int(request.GET.get('voter_index_start', 0))
    voter_list_of_dicts = []
    status = ''
    success = True

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'analytics_admin'}
    if not voter_has_authority(request, authority_required):
        status += "VOTER_LIST_ANALYTICS_VIEW-MISSING_AUTHORITY "
        success = False
        json_data = {
            'status':                   status,
            'success':                  success,
            'show_signed_in_voters':    show_signed_in_voters,
            'voter_count_total':        voter_count_total,
            'voter_count_requested':    voter_count_requested,
            'voter_count_returned':     voter_count_returned,
            'voter_index_start':        voter_index_start,
            'voter_index_end':          voter_index_end,
            'voter_list':               voter_list_of_dicts,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_queryset = Voter.objects.using('readonly').all()
    if show_signed_in_voters:
        voter_queryset = voter_queryset.filter(is_signed_in_cached=True)
    voter_count_total = voter_queryset.count()
    voter_queryset = voter_queryset.order_by('-date_last_changed')
    if positive_value_exists(voter_count_requested):
        if positive_value_exists(voter_index_start):
            voter_list = voter_queryset[voter_index_start:voter_count_requested]
        else:
            voter_list = voter_queryset[:voter_count_requested]
    elif positive_value_exists(voter_index_start):
        voter_list = voter_queryset[voter_index_start:voter_count_requested]
    else:
        voter_list = voter_queryset[:voter_count_requested_default]
    voter_count_returned = voter_list.count()
    if positive_value_exists((voter_index_start + voter_count_returned)):
        voter_index_end = voter_index_start + voter_count_returned - 1
    else:
        voter_index_end = 0

    voter_list_of_we_vote_ids = []
    for voter in voter_list:
        voter_dict = {
            'we_vote_id': voter.we_vote_id,
        }
        voter_list_of_dicts.append(voter_dict)
        voter_list_of_we_vote_ids.append(voter.we_vote_id)

    if show_we_vote_id_only:
        json_data = voter_list_of_we_vote_ids
    else:
        json_data = {
            'status':                   status,
            'success':                  success,
            'show_signed_in_voters':    show_signed_in_voters,
            'voter_count_total':        voter_count_total,
            'voter_count_requested':    voter_count_requested,
            'voter_count_returned':     voter_count_returned,
            'voter_index_start':        voter_index_start,
            'voter_index_end':          voter_index_end,
            'voter_list':               voter_list_of_dicts,
        }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def save_analytics_action_view(request):  # saveAnalyticsAction
    status = ""
    success = False
    missing_required_variable = False
    voter_id = 0
    voter_we_vote_id = ""
    is_signed_in = False
    state_code_from_ip_address = ""  # If a state_code is NOT passed in, we want to get the state_code from ip address
    voter_device_id_for_storage = ""
    date_as_integer = 0

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    action_constant = convert_to_int(request.GET.get('action_constant', 0))
    state_code = request.GET.get('state_code', '')  # If a state code is passed in, we want to use it
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    organization_id = convert_to_int(request.GET.get('organization_id', 0))
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', '')
    politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
    seo_friendly_path = request.GET.get('seo_friendly_path', '')
    user_agent_string = request.headers['user-agent']

    # robot-detection is used for detecting web bots only and django-user-agents is used for device detection
    user_agent_object = get_user_agent(request)
    is_bot = user_agent_object.is_bot or robot_detection.is_robot(user_agent_string)
    is_mobile = user_agent_object.is_mobile
    is_desktop = user_agent_object.is_pc
    is_tablet = user_agent_object.is_tablet

    # We use the lighter call to VoterDeviceLinkManager instead of VoterManager until we know there is an entry
    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(voter_device_id, read_only=True)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
        voter_id = voter_device_link.voter_id
        state_code_from_ip_address = voter_device_link.state_code
        voter_manager = VoterManager()
        # There is 5-second delay in WebApp before we save to AnalyticsAction, so ok to use 'readonly' database
        voter_results = voter_manager.retrieve_voter_by_id(voter_id, read_only=True)
        if positive_value_exists(voter_results['voter_found']):
            voter = voter_results['voter']
            voter_we_vote_id = voter.we_vote_id
            is_signed_in = voter.is_signed_in()
    else:
        voter_device_id_for_storage = voter_device_id

    action_requires_organization_ids = True if action_constant in ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS else False
    if action_requires_organization_ids:
        # If here, make sure we have both organization ids
        organization_manager = OrganizationManager()
        if positive_value_exists(organization_we_vote_id) and not positive_value_exists(organization_id):
            organization_id = organization_manager.fetch_organization_id(organization_we_vote_id)
        elif positive_value_exists(organization_id) and not positive_value_exists(organization_we_vote_id):
            organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(organization_id)

        if not positive_value_exists(organization_we_vote_id):
            status += "MISSING_ORGANIZATION_WE_VOTE_ID "
            success = False
            missing_required_variable = True
        if not positive_value_exists(organization_id):
            status += "MISSING_ORGANIZATION_ID "
            success = False
            missing_required_variable = True

    if not positive_value_exists(state_code):
        state_code = state_code_from_ip_address

    if missing_required_variable:
        json_data = {
            'status':                   status,
            'success':                  success,
            'voter_device_id':          voter_device_id,
            'action_constant':          action_constant,
            'state_code':               state_code,
            'is_signed_in':             is_signed_in,
            'google_civic_election_id': google_civic_election_id,
            'organization_we_vote_id':  organization_we_vote_id,
            'organization_id':          organization_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'politician_we_vote_id':    politician_we_vote_id,
            'date_as_integer':          date_as_integer,
            'user_agent':               user_agent_string,
            'is_bot':                   is_bot,
            'is_mobile':                is_mobile,
            'is_desktop':               is_desktop,
            'is_tablet':                is_tablet,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = save_analytics_action_for_api(
        action_constant=action_constant,
        voter_we_vote_id=voter_we_vote_id,
        voter_id=voter_id,
        is_signed_in=is_signed_in,
        state_code=state_code,
        organization_we_vote_id=organization_we_vote_id,
        organization_id=organization_id,
        google_civic_election_id=google_civic_election_id,
        user_agent_string=user_agent_string,
        is_bot=is_bot,
        is_mobile=is_mobile,
        is_desktop=is_desktop,
        is_tablet=is_tablet,
        ballot_item_we_vote_id=ballot_item_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        seo_friendly_path=seo_friendly_path,
        voter_device_id=voter_device_id_for_storage)

    status += results['status']
    json_data = {
        'status':                   status,
        'success':                  results['success'],
        'voter_device_id':          voter_device_id,
        'action_constant':          action_constant,
        'state_code':               state_code,
        'is_signed_in':             is_signed_in,
        'google_civic_election_id': google_civic_election_id,
        'organization_we_vote_id':  organization_we_vote_id,
        'organization_id':          organization_id,
        'politician_we_vote_id':    results['politician_we_vote_id'],
        'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        'date_as_integer':          results['date_as_integer'],
        'user_agent':               user_agent_string,
        'is_bot':                   is_bot,
        'is_mobile':                is_mobile,
        'is_desktop':               is_desktop,
        'is_tablet':                is_tablet,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
