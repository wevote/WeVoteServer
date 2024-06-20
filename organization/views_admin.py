# organization/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import full_domain_string_available, merge_these_two_organizations,\
    move_organization_followers_to_another_organization, move_organization_membership_link_to_another_organization, \
    move_organization_team_member_entries_to_another_organization, organizations_import_from_master_server, \
    organization_politician_match, push_organization_data_to_other_table_caches, subdomain_string_available
from .controllers_fastly import add_wevote_subdomain_to_fastly, add_subdomain_route53_record, \
    get_wevote_subdomain_status
from .models import GROUP, INDIVIDUAL, Organization, OrganizationChangeLog, OrganizationReservedDomain, \
    OrganizationTeamMember, ORGANIZATION_UNIQUE_IDENTIFIERS
from base64 import b64encode
from admin_tools.views import redirect_to_sign_in_page
from campaign.controllers import move_campaignx_to_another_organization
from campaign.models import CampaignXListedByOrganization, CampaignXManager
from candidate.models import CandidateCampaign, CandidateListManager, CandidateManager, \
    PROFILE_IMAGE_TYPE_UNKNOWN, PROFILE_IMAGE_TYPE_UPLOADED
from config.base import get_environment_variable
from datetime import datetime
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
# TODO: July 2021: donate.models has been abandoned, this is still in place to allow the app to compile.
from donate.models import MasterFeaturePackage
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_deleted_exception, handle_record_not_found_exception
from election.controllers import retrieve_election_id_list_by_year_list, retrieve_upcoming_election_id_list
from election.models import Election, ElectionManager
from image.controllers import create_resized_images
from import_export_twitter.controllers import refresh_twitter_organization_details
from import_export_vote_smart.models import VoteSmartSpecialInterestGroupManager
from issue.models import ALPHABETICAL_ASCENDING, IssueListManager, IssueManager, \
    OrganizationLinkToIssueList, OrganizationLinkToIssueManager, MOST_LINKED_ORGANIZATIONS
import json
from measure.models import ContestMeasure, ContestMeasureListManager, ContestMeasureManager
import operator
from organization.models import OrganizationListManager, OrganizationManager, ORGANIZATION_TYPE_MAP, UNKNOWN
from organization.controllers import figure_out_organization_conflict_values, \
    organization_retrieve_tweets_from_twitter, organization_analyze_tweets, organization_save_photo_from_file_reader
from position.models import PositionEntered, PositionForFriends, PositionListManager, PositionManager, \
    INFORMATION_ONLY, OPPOSE, STILL_DECIDING, SUPPORT
from twitter.models import TwitterLinkToOrganization, TwitterUserManager
from voter.models import fetch_voter_from_voter_device_link, retrieve_voter_authority, voter_has_authority, VoterManager
from voter_guide.models import VoterGuideManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_api_device_id, \
    extract_instagram_handle_from_text_string, extract_twitter_handle_from_text_string, \
    positive_value_exists, STATE_CODE_MAP
from wevote_functions.functions_date import convert_date_to_date_as_integer
from wevote_settings.constants import ELECTION_YEARS_AVAILABLE


ORGANIZATION_STANCE_CHOICES = (
    (SUPPORT,           'We Support'),
    (OPPOSE,            'We Oppose'),
    (INFORMATION_ONLY,  'Information Only - No stance'),
    (STILL_DECIDING,    'We Are Still Deciding Our Stance'),
)
ORGANIZATIONS_SYNC_URL = get_environment_variable("ORGANIZATIONS_SYNC_URL")  # organizationsSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def compare_two_organizations_for_merge_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization1_we_vote_id = request.GET.get('organization1_we_vote_id', 0)
    organization2_we_vote_id = request.GET.get('organization2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    organization_manager = OrganizationManager()
    organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization1_we_vote_id)
    if not organization_results['organization_found']:
        messages.add_message(request, messages.ERROR, "Organization1 not found.")
        return HttpResponseRedirect(reverse('organization:organization_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    organization_option1_for_template = organization_results['organization']

    organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization2_we_vote_id)
    if not organization_results['organization_found']:
        messages.add_message(request, messages.ERROR, "Organization2 not found.")
        return HttpResponseRedirect(reverse('organization:organization_position_list',
                                            args=(organization_option1_for_template.id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    organization_option2_for_template = organization_results['organization']

    organization_merge_conflict_values = figure_out_organization_conflict_values(
        organization_option1_for_template, organization_option2_for_template)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_organization_merge_form(
        request, organization_option1_for_template,
        organization_option2_for_template,
        organization_merge_conflict_values,
        remove_duplicate_process)


@login_required
def edit_team_members_process_view(request):
    """
    Process the edit team members form
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    team_member_voter_we_vote_id = request.POST.get('team_member_voter_we_vote_id', None)
    if positive_value_exists(team_member_voter_we_vote_id):
        team_member_voter_we_vote_id = team_member_voter_we_vote_id.strip()
    can_edit_campaignx_owned_by_organization = \
        positive_value_exists(request.POST.get('can_edit_campaignx_owned_by_organization', False))
    can_manage_team_members = positive_value_exists(request.POST.get('can_manage_team_members', False))
    can_send_updates_for_campaignx_owned_by_organization = \
        positive_value_exists(request.POST.get('can_send_updates_for_campaignx_owned_by_organization', False))
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    organization_id = convert_to_int(request.POST.get('organization_id', None))
    organization_we_vote_id = request.POST.get('organization_we_vote_id', None)
    state_code = request.POST.get('state_code', '')

    voter_manager = VoterManager()

    # Create new OrganizationTeamMember
    if positive_value_exists(team_member_voter_we_vote_id):
        if 'voter' not in team_member_voter_we_vote_id:
            messages.add_message(request, messages.ERROR, 'Valid VoterWeVoteId missing.')
        else:
            do_not_create = False
            link_already_exists = False
            status = ""
            # Does it already exist?
            try:
                OrganizationTeamMember.objects.get(
                    voter_we_vote_id=team_member_voter_we_vote_id,
                    organization_we_vote_id=organization_we_vote_id)
                link_already_exists = True
            except OrganizationTeamMember.DoesNotExist:
                link_already_exists = False
            except Exception as e:
                do_not_create = True
                messages.add_message(request, messages.ERROR, 'Link already exists.')
                status += "ADD_TEAM_MEMBER_ALREADY_EXISTS: " + str(e) + " "

            if not do_not_create and not link_already_exists:
                # Now create new link
                voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                    voter_we_vote_id=team_member_voter_we_vote_id,
                    read_only=True)
                team_member_name = ''
                team_member_organization_we_vote_id = ''
                we_vote_hosted_profile_image_url_tiny = ''
                if voter_results['voter_found']:
                    team_member_name = voter_results['voter'].get_full_name()
                    team_member_organization_we_vote_id = voter_results['voter'].linked_organization_we_vote_id
                    we_vote_hosted_profile_image_url_tiny = voter_results['voter'].we_vote_hosted_profile_image_url_tiny
                try:
                    # Create the OrganizationTeamMember link
                    OrganizationTeamMember.objects.create(
                        can_edit_campaignx_owned_by_organization=can_edit_campaignx_owned_by_organization,
                        can_manage_team_members=can_manage_team_members,
                        can_send_updates_for_campaignx_owned_by_organization=can_send_updates_for_campaignx_owned_by_organization,
                        organization_we_vote_id=organization_we_vote_id,
                        team_member_name=team_member_name,
                        team_member_organization_we_vote_id=team_member_organization_we_vote_id,
                        voter_we_vote_id=team_member_voter_we_vote_id,
                        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                    )
                    # can_edit_organization = models.BooleanField(default=True)
                    # can_moderate_campaignx_owned_by_organization = models.BooleanField(default=True)

                    messages.add_message(request, messages.INFO, 'New OrganizationTeamMember created.')
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         'Could not create OrganizationTeamMember.'
                                         ' {error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    # ##################################
    # Deleting or Adding a new OrganizationTeamMember
    organization_manager = OrganizationManager()
    team_member_list = organization_manager.retrieve_team_member_list(
        organization_we_vote_id=organization_we_vote_id,
        read_only=False
    )
    for team_member in team_member_list:
        if positive_value_exists(team_member.voter_we_vote_id):
            variable_name = "delete_team_member_" + str(team_member.id)
            delete_team_member = positive_value_exists(request.POST.get(variable_name, False))
            if positive_value_exists(delete_team_member):
                team_member.delete()
                messages.add_message(request, messages.INFO, 'Deleted OrganizationTeamMember.')
            else:
                # Refresh voter information
                voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                    voter_we_vote_id=team_member.voter_we_vote_id,
                    read_only=True)
                if voter_results['voter_found']:
                    team_member.team_member_name = voter_results['voter'].get_full_name()
                    team_member.team_member_organization_we_vote_id = \
                        voter_results['voter'].linked_organization_we_vote_id
                    team_member.we_vote_hosted_profile_image_url_tiny = \
                        voter_results['voter'].we_vote_hosted_profile_image_url_tiny

                # can_edit_campaignx_owned_by_organization
                variable_name = "can_edit_campaignx_owned_by_organization_" + str(team_member.id)
                can_edit_campaignx_owned_by_organization = positive_value_exists(request.POST.get(variable_name, False))
                exists_variable_name = "can_edit_campaignx_owned_by_organization_" + str(team_member.id) + "_exists"
                can_edit_campaignx_owned_by_organization_exists = request.POST.get(exists_variable_name, None)
                if can_edit_campaignx_owned_by_organization_exists:
                    team_member.can_edit_campaignx_owned_by_organization = can_edit_campaignx_owned_by_organization

                # can_manage_team_members
                variable_name = "can_manage_team_members_" + str(team_member.id)
                can_manage_team_members = positive_value_exists(request.POST.get(variable_name, False))
                exists_variable_name = "can_manage_team_members_" + str(team_member.id) + "_exists"
                can_manage_team_members_exists = request.POST.get(exists_variable_name, None)
                if can_manage_team_members_exists:
                    team_member.can_manage_team_members = can_manage_team_members

                # can_send_updates_for_campaignx_owned_by_organization
                variable_name = "can_send_updates_for_campaignx_owned_by_organization_" + str(team_member.id)
                can_send_updates_for_campaignx_owned_by_organization = \
                    positive_value_exists(request.POST.get(variable_name, False))
                exists_variable_name = "can_edit_campaignx_owned_by_organization_" + str(team_member.id) + "_exists"
                can_send_updates_for_campaignx_owned_by_organization_exists = \
                    request.POST.get(exists_variable_name, None)
                if can_send_updates_for_campaignx_owned_by_organization_exists:
                    team_member.can_send_updates_for_campaignx_owned_by_organization = \
                        can_send_updates_for_campaignx_owned_by_organization
                team_member.save()

    return HttpResponseRedirect(reverse('organization:edit_team_members', args=(organization_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def edit_team_members_view(request, organization_id=0, organization_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    organization_manager = OrganizationManager()
    organization_on_stage = Organization()
    results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)

    if results['organization_found']:
        organization_on_stage = results['organization']
        organization_we_vote_id = organization_on_stage.we_vote_id

    organization_manager = OrganizationManager()
    team_member_list_modified = []
    team_member_list = organization_manager.retrieve_team_member_list(
        organization_we_vote_id=organization_we_vote_id,
        read_only=False
    )

    voter_manager = VoterManager()
    for organization_team_member in team_member_list:
        if positive_value_exists(organization_team_member.voter_we_vote_id):
            results = voter_manager.retrieve_voter_by_we_vote_id(
                voter_we_vote_id=organization_team_member.voter_we_vote_id,
                read_only=False,
            )
            if results['voter_found']:
                organization_team_member.team_member_name = results['voter'].get_full_name()
                organization_team_member.we_vote_hosted_profile_image_url_tiny = \
                    results['voter'].we_vote_hosted_profile_image_url_tiny
                organization_team_member.team_member_organization_we_vote_id = \
                    results['voter'].linked_organization_we_vote_id
                organization_team_member.save()
        team_member_list_modified.append(organization_team_member)

    template_values = {
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'organization':             organization_on_stage,
        'state_code':               state_code,
        'team_member_list':         team_member_list_modified,
    }
    return render(request, 'organization/edit_team_members.html', template_values)

@login_required
def organization_analyze_tweets_view(request, organization_we_vote_id):
    """

    :param request:
    :param organization_we_vote_id:
    :return:
    """
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', False)

    org_hashtags = organization_analyze_tweets(organization_we_vote_id)
    messages.add_message(request, messages.INFO, 'Tweets stored locally: {cached_tweets}, '
                                                 'Hash tags retrieved: {hash_tags_retrieved}, '
                                                 'Number of unique hashtags found in cached tweets: '
                                                 '{unique_hashtags}, '
                                                 'Endorser links to hashtags: '
                                                 '{organization_link_to_hashtag_results}'
                                                 ''.format(cached_tweets=org_hashtags['cached_tweets'],
                                                           hash_tags_retrieved=org_hashtags['hash_tags_retrieved'],
                                                           unique_hashtags=org_hashtags['unique_hashtags'],
                                                           organization_link_to_hashtag_results=
                                                           org_hashtags['organization_link_to_hashtag_results']))
    return HttpResponseRedirect(reverse('organization:organization_we_vote_id_position_list',
                                        args=(organization_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) + "&state_code=" +
                                str(state_code))


@login_required
def organization_retrieve_tweets_view(request, organization_we_vote_id):
    """
    For one organization, retrieve X Tweets, and capture all #Hashtags used.

    :param request:
    :param organization_we_vote_id:
    :return:
    """
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', False)

    org_tweets_results = organization_retrieve_tweets_from_twitter(organization_we_vote_id)
    messages.add_message(request, messages.INFO, 'Endorser retrieve tweets executed, '
                                                 'Tweets retrieved: {tweets_saved}, '
                                                 'Tweets not retrieved: {tweets_not_saved}, '
                                                 ''.format(tweets_saved=org_tweets_results['tweets_saved'],
                                                           tweets_not_saved=org_tweets_results['tweets_not_saved'],))
    return HttpResponseRedirect(reverse('organization:organization_we_vote_id_position_list',
                                        args=(organization_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) + "&state_code=" +
                                str(state_code))


# This page does not need to be protected.
def organizations_sync_out_view(request):  # organizationsSyncOut
    state_served_code = request.GET.get('state_served_code', '')

    try:
        organization_queryset = Organization.objects.using('readonly').all()
        organization_queryset = organization_queryset.exclude(organization_type__iexact=INDIVIDUAL)
        if positive_value_exists(state_served_code):
            organization_queryset = organization_queryset.filter(state_served_code__iexact=state_served_code)
        organization_list_dict = organization_queryset.values(
            'we_vote_id', 'organization_name', 'organization_type',
            'organization_description', 'state_served_code',
            'organization_website', 'organization_email',
            'organization_image', 'organization_twitter_handle',
            'twitter_user_id', 'twitter_followers_count',
            'twitter_description', 'twitter_location', 'twitter_name',
            'twitter_profile_image_url_https',
            'twitter_profile_background_image_url_https',
            'twitter_profile_banner_url_https', 'organization_facebook',
            'vote_smart_id', 'organization_contact_form_url', 'organization_contact_name',
            'organization_address', 'organization_city',
            'organization_state', 'organization_zip',
            'organization_phone1', 'organization_phone2',
            'organization_fax', 'wikipedia_page_title',
            'wikipedia_page_id', 'wikipedia_photo_url',
            'wikipedia_thumbnail_url', 'wikipedia_thumbnail_width',
            'wikipedia_thumbnail_height', 'ballotpedia_page_title',
            'ballotpedia_photo_url', 'we_vote_hosted_profile_image_url_large',
            'we_vote_hosted_profile_image_url_medium', 'we_vote_hosted_profile_image_url_tiny'
        )
        if organization_list_dict:
            organization_list_json = list(organization_list_dict)
            return HttpResponse(json.dumps(organization_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'ORGANIZATION_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def organizations_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in ORGANIZATIONS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = organizations_import_from_master_server(request, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Endorsers import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Duplicates skipped: '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required
def organization_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = \
        {'partner_organization', 'political_data_manager', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    limit_to_opinions_in_state_code = request.GET.get('limit_to_opinions_in_state_code', '')
    limit_to_opinions_in_this_year = convert_to_int(request.GET.get('limit_to_opinions_in_this_year', 0))
    organization_search = request.GET.get('organization_search', '')
    organization_type_filter = request.GET.get('organization_type_filter', '')
    selected_issue_vote_id_list = request.GET.getlist('selected_issues', '')
    sort_by = request.GET.get('sort_by', '')
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_issues = request.GET.get('show_issues', '')
    show_organizations_without_email = positive_value_exists(request.GET.get('show_organizations_without_email', False))
    show_twitter_updates_failing = positive_value_exists(request.GET.get('show_twitter_updates_failing', False))
    show_organizations_to_be_analyzed = \
        positive_value_exists(request.GET.get('show_organizations_to_be_analyzed', False))
    show_up_to_1000 = request.GET.get('show_up_to_1000', False)
    show_up_to_2000 = request.GET.get('show_up_to_2000', False)

    messages_on_stage = get_messages(request)
    organization_list_query = Organization.objects.all()
    if positive_value_exists(sort_by):
        if sort_by == "twitter":
            organization_list_query = \
                organization_list_query.order_by('organization_name').order_by('-twitter_followers_count')
        else:
            organization_list_query = organization_list_query.order_by('organization_name')
    else:
        organization_list_query = organization_list_query.order_by('organization_name')

    # wv02org35759
    if positive_value_exists(organization_search):
        # Do not limit search
        pass
    elif positive_value_exists(show_organizations_without_email):
        organization_list_query = organization_list_query.filter(
            Q(organization_email__isnull=True) |
            Q(organization_email__exact='')
        )

    if positive_value_exists(show_twitter_updates_failing):
        organization_list_query = organization_list_query.filter(organization_twitter_updates_failing=True)

    if positive_value_exists(show_organizations_to_be_analyzed):
        organization_list_query = organization_list_query.filter(issue_analysis_done=False)

    if positive_value_exists(state_code):
        organization_list_query = organization_list_query.filter(state_served_code__iexact=state_code)

    if positive_value_exists(organization_type_filter):
        if organization_type_filter == UNKNOWN:
            # Make sure to also show organizations that are not specified
            organization_list_query = organization_list_query.filter(
                Q(organization_type__iexact=organization_type_filter) |
                Q(organization_type__isnull=True) |
                Q(organization_type__exact='')
            )
        else:
            organization_list_query = organization_list_query.filter(organization_type__iexact=organization_type_filter)
    elif positive_value_exists(organization_search):
        # Do not remove individuals from search
        pass
    else:
        # By default, don't show individuals
        organization_list_query = organization_list_query.exclude(organization_type__iexact=INDIVIDUAL)

    link_issue_list_manager = OrganizationLinkToIssueList()
    issue_list_manager = IssueListManager()

    # Only show organizations linked to specific issues
    # 2017-12-12 DALE I'm not sure this is being used yet...
    issues_selected = False
    issue_list = []
    if positive_value_exists(selected_issue_vote_id_list):
        issues_selected = True
        new_issue_list = []
        issue_list_manager = IssueListManager()
        issue_list_results = issue_list_manager.retrieve_issues()
        if issue_list_results["issue_list_found"]:
            issue_list = issue_list_results["issue_list"]
            for issue in issue_list:
                if issue.we_vote_id in selected_issue_vote_id_list:
                    issue.selected = True
                new_issue_list.append(issue)
            issue_list = new_issue_list

            organization_we_vote_id_list_result = link_issue_list_manager.\
                retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list(selected_issue_vote_id_list)
            organization_we_vote_id_list = organization_we_vote_id_list_result['organization_we_vote_id_list']
            # we decided to not deal with case-insensitivity, in favor of using '__in'
            organization_list_query = organization_list_query.filter(we_vote_id__in=organization_we_vote_id_list)

    if positive_value_exists(organization_search):
        search_words = organization_search.split()
        for one_word in search_words:
            filters = []

            new_filter = Q(chosen_domain_string__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(chosen_domain_string2__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(chosen_domain_string3__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(chosen_subdomain_string__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_twitter_handle__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_website__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(twitter_description__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(vote_smart_id__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                organization_list_query = organization_list_query.filter(final_filters)
    else:
        # This is the default organization list
        filters = []

        new_filter = Q(organization_name="")
        filters.append(new_filter)

        new_filter = Q(organization_name__startswith="Voter-")
        filters.append(new_filter)

        new_filter = Q(organization_name__startswith="wv")
        filters.append(new_filter)

        # Add the first query
        if len(filters):
            final_filters = filters.pop()

            # ...and "OR" the remaining items in the list
            for item in filters:
                final_filters |= item

            # NOTE this is "exclude"
            organization_list_query = organization_list_query.exclude(final_filters)

    # Limit to organizations with opinions in this year and state
    position_list_manager = PositionListManager()
    elections_not_found_in_year = False
    google_civic_election_id_list = []
    if positive_value_exists(limit_to_opinions_in_this_year):
        election_year_list_to_show = [limit_to_opinions_in_this_year]
        google_civic_election_id_list = \
            retrieve_election_id_list_by_year_list(election_year_list_to_show=election_year_list_to_show)
        if not positive_value_exists(len(google_civic_election_id_list)):
            elections_not_found_in_year = True

    if elections_not_found_in_year:
        # No organizations should be found
        organization_we_vote_id_list = []
        organization_list_query = organization_list_query.filter(we_vote_id__in=organization_we_vote_id_list)
    elif positive_value_exists(len(google_civic_election_id_list)) or \
            positive_value_exists(limit_to_opinions_in_state_code):
        results = position_list_manager.retrieve_organization_we_vote_id_list_for_election_and_state(
            google_civic_election_id_list=google_civic_election_id_list,
            state_code=limit_to_opinions_in_state_code)
        if results['success']:
            organization_we_vote_id_list = results['organization_we_vote_id_list']
            organization_list_query = organization_list_query.filter(we_vote_id__in=organization_we_vote_id_list)

    organization_count = organization_list_query.count()
    messages.add_message(request, messages.INFO,
                         '{organization_count:,} endorsers found.'.format(organization_count=organization_count))

    # Limit to only showing 200 on screen
    if positive_value_exists(show_up_to_1000):
        organization_list = organization_list_query[:1000]
    elif positive_value_exists(show_up_to_2000):
        organization_list = organization_list_query[:2000]
    elif positive_value_exists(show_all):
        organization_list = organization_list_query
    else:
        organization_list = organization_list_query[:200]

    # Now loop through these organizations and add on the linked_issues_count
    modified_organization_list = []
    special_interest_group_manager = VoteSmartSpecialInterestGroupManager()
    for one_organization in organization_list:
        # Turned off for now
        # one_organization.linked_issues_count = \
        #     link_issue_list_manager.fetch_issue_count_for_organization(0, one_organization.we_vote_id)
        if positive_value_exists(show_issues):
            # We want to look up the issues retrieved from Vote Smart and display them
            # if positive_value_exists(one_organization.linked_issues_count):
            show_hidden_issues = True
            one_organization.display_we_vote_issues = \
                issue_list_manager.fetch_organization_issues_for_display(
                    one_organization.we_vote_id, MOST_LINKED_ORGANIZATIONS, show_hidden_issues)
            if positive_value_exists(one_organization.vote_smart_id):
                one_organization.display_vote_smart_issues = \
                    special_interest_group_manager.fetch_vote_smart_organization_issues_for_display(
                        one_organization.vote_smart_id)
        modified_organization_list.append(one_organization)

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    organization_types_map = ORGANIZATION_TYPE_MAP
    # Sort by organization_type value (instead of key)
    organization_types_list = sorted(organization_types_map.items(), key=operator.itemgetter(1))

    template_values = {
        'candidate_we_vote_id':     candidate_we_vote_id,
        'election_years_available': ELECTION_YEARS_AVAILABLE,
        'google_civic_election_id': google_civic_election_id,
        'issue_list':               issue_list,
        'issues_selected':          issues_selected,
        'limit_to_opinions_in_state_code': limit_to_opinions_in_state_code,
        'limit_to_opinions_in_this_year': limit_to_opinions_in_this_year,
        'messages_on_stage':        messages_on_stage,
        'organization_type_filter': organization_type_filter,
        'organization_types':       organization_types_list,
        'organization_list':        modified_organization_list,
        'organization_search':      organization_search,
        'show_all':                 show_all,
        'show_issues':              show_issues,
        'show_organizations_without_email': show_organizations_without_email,
        'show_organizations_to_be_analyzed': show_organizations_to_be_analyzed,
        'show_twitter_updates_failing': show_twitter_updates_failing,
        'show_up_to_1000':          show_up_to_1000,
        'show_up_to_2000':          show_up_to_2000,
        'sort_by':                  sort_by,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'organization/organization_list.html', template_values)


@login_required
def organization_merge_process_view(request):
    """
    Process the merging of two organizations using the Admin tool
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_manager = OrganizationManager()

    merge = request.POST.get('merge', False)
    skip = request.POST.get('skip', False)

    # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
    organization1_we_vote_id = request.POST.get('organization1_we_vote_id', 0)
    organization2_we_vote_id = request.POST.get('organization2_we_vote_id', 0)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    redirect_to_organization_list = request.POST.get('redirect_to_organization_list', False)
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    state_code = request.POST.get('state_code', '')
    status = ''

    if positive_value_exists(skip):
        messages.add_message(request, messages.ERROR, 'Skip is not implemented for organizations yet.')
        # results = organization_manager.update_or_create_organizations_are_not_duplicates(
        #     organization1_we_vote_id, organization2_we_vote_id)
        # if not results['new_organizations_are_not_duplicates_created']:
        #     messages.add_message(request, messages.ERROR, 'Could not save organizations_are_not_duplicates entry: ' +
        #                          results['status'])
        # messages.add_message(request, messages.INFO, 'Prior organizations skipped, and not merged.')
        # return HttpResponseRedirect(reverse('organization:find_and_merge_duplicate_organizations', args=()) +
        #                             "?google_civic_election_id=" + str(google_civic_election_id) +
        #                             "&state_code=" + str(state_code))
        return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code) +
                                    "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                    "&organization2_we_vote_id=" + str(organization2_we_vote_id))

    # Check to make sure that organization2 isn't linked to a voter. If so, cancel out for now.
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization2_we_vote_id, read_only=True)
    if results['voter_found']:
        status += "MERGE_PROCESS_VIEW-ORGANIZATION2_LINKED_TO_A_VOTER "
        messages.add_message(request, messages.ERROR, status)
        return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code) +
                                    "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                    "&organization2_we_vote_id=" + str(organization2_we_vote_id))

    twitter_user_manager = TwitterUserManager()
    organization1_results = \
        twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization1_we_vote_id)

    organization2_results = \
        twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization2_we_vote_id)
    if not organization1_results['success'] or not organization2_results['success']:
        status += organization1_results['status']
        status += organization2_results['status']
        messages.add_message(request, messages.ERROR,
                             status +
                             'Failed to retrieve TwitterLinkToOrganization entries. '
                             'Merge cannot proceed.')
        return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code) +
                                    "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                    "&organization2_we_vote_id=" + str(organization2_we_vote_id))
    elif organization1_results['twitter_link_to_organization_found'] and \
            organization2_results['twitter_link_to_organization_found']:
        messages.add_message(request, messages.ERROR,
                             'Organization1 and Organization2 both have TwitterLinkToOrganization entries. '
                             'Merge cannot proceed.')
        return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code) +
                                    "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                    "&organization2_we_vote_id=" + str(organization2_we_vote_id))
    elif not organization1_results['twitter_link_to_organization_found'] and \
            organization2_results['twitter_link_to_organization_found']:
        # Move organization2 twitter link to organization1
        try:
            twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                organization_we_vote_id=organization2_we_vote_id)
            twitter_link_to_organization.organization_we_vote_id = organization1_we_vote_id
            twitter_link_to_organization.save()
        except Exception as e:
            status += "FAILED_TO_MIGRATE_TWITTER_LINK_TO_ORGANIZATION_TO_ORG1: " + str(e) + " "
            messages.add_message(request, messages.ERROR, status)
            return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code) +
                                        "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                        "&organization2_we_vote_id=" + str(organization2_we_vote_id))

    organization1_results = organization_manager.retrieve_organization_from_we_vote_id(organization1_we_vote_id)
    if organization1_results['organization_found']:
        organization1_on_stage = organization1_results['organization']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve organization 1.')
        return HttpResponseRedirect(reverse('organization:organization_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    organization2_results = organization_manager.retrieve_organization_from_we_vote_id(organization2_we_vote_id)
    if organization2_results['organization_found']:
        organization2_on_stage = organization2_results['organization']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve organization 2.')
        return HttpResponseRedirect(reverse('organization:organization_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    from_organization_id = organization2_on_stage.id
    from_organization_we_vote_id = organization2_on_stage.we_vote_id
    to_organization_id = organization1_on_stage.id
    to_organization_we_vote_id = organization1_on_stage.we_vote_id

    # Make sure we have both from_organization values
    if positive_value_exists(from_organization_id) and not positive_value_exists(from_organization_we_vote_id):
        from_organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(from_organization_id)
    elif positive_value_exists(from_organization_we_vote_id) and not positive_value_exists(from_organization_id):
        from_organization_id = organization_manager.fetch_organization_id(from_organization_we_vote_id)

    # Make sure we have both to_organization values
    if positive_value_exists(to_organization_id) and not positive_value_exists(to_organization_we_vote_id):
        to_organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(to_organization_id)
    elif positive_value_exists(to_organization_we_vote_id) and not positive_value_exists(to_organization_id):
        to_organization_id = organization_manager.fetch_organization_id(to_organization_we_vote_id)

    # If anyone is following organization2, move those followers to organization1
    move_organization_followers_results = move_organization_followers_to_another_organization(
        from_organization_id, from_organization_we_vote_id,
        to_organization_id, to_organization_we_vote_id)
    status += " " + move_organization_followers_results['status']
    if positive_value_exists(move_organization_followers_results['follow_entries_not_moved']):
        messages.add_message(request, messages.ERROR, status)
        return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code) +
                                    "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                    "&organization2_we_vote_id=" + str(organization2_we_vote_id))

    # If anyone has been linked with external_voter_id as a member of the old voter's organization,
    #  move those followers to the new voter's organization
    move_organization_membership_link_results = move_organization_membership_link_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += " " + move_organization_membership_link_results['status']
    if positive_value_exists(move_organization_membership_link_results['membership_link_entries_not_moved']):
        messages.add_message(request, messages.ERROR, status)
        return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code) +
                                    "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                    "&organization2_we_vote_id=" + str(organization2_we_vote_id))

    move_organization_team_member_results = move_organization_team_member_entries_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += " " + move_organization_team_member_results['status']
    if not positive_value_exists(move_organization_team_member_results['success']):
        messages.add_message(request, messages.ERROR, status)
        return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code) +
                                    "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                    "&organization2_we_vote_id=" + str(organization2_we_vote_id))

    # Gather choices made from merge form
    conflict_values = figure_out_organization_conflict_values(organization1_on_stage, organization2_on_stage)
    admin_merge_choices = {}
    for attribute in ORGANIZATION_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            choice = request.POST.get(attribute + '_choice', '')
            if organization2_we_vote_id == choice:
                admin_merge_choices[attribute] = getattr(organization2_on_stage, attribute)
        elif conflict_value == "CANDIDATE2":
            admin_merge_choices[attribute] = getattr(organization2_on_stage, attribute)

    merge_results = \
        merge_these_two_organizations(organization1_we_vote_id, organization2_we_vote_id, admin_merge_choices)

    if not positive_value_exists(merge_results['organizations_merged']):
        # NOTE: We could also redirect to a page to look specifically at these two organizations, but this should
        # also get you back to looking at the two organizations
        error_message = "ORGANIZATION_COMPARISON_PROBLEM: " + merge_results['status']
        messages.add_message(request, messages.ERROR, error_message)
        return HttpResponseRedirect(reverse('organization:compare_two_organizations_for_merge', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code) +
                                    "&organization1_we_vote_id=" + str(organization1_we_vote_id) +
                                    "&organization2_we_vote_id=" + str(organization2_we_vote_id))

    organization = merge_results['organization']
    to_organization_name = organization.organization_name

    move_campaignx_results = move_campaignx_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id, to_organization_name)
    status += " " + move_campaignx_results['status']

    messages.add_message(request, messages.INFO, "Endorser '{organization_name}' merged."
                                                 "".format(organization_name=organization.organization_name))

    if redirect_to_organization_list:
        return HttpResponseRedirect(reverse('organization:organization_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    # if remove_duplicate_process:
    #     return HttpResponseRedirect(reverse('organization:find_and_merge_duplicate_organizations', args=()) +
    #                                 "?google_civic_election_id=" + str(google_civic_election_id) +
    #                                 "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization1_on_stage.id,)))


@login_required
def organization_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # A positive value in google_civic_election_id means we want to create a voter guide for this org for this election
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'upcoming_election_list':   upcoming_election_list,
        'google_civic_election_id': google_civic_election_id,
        'state_list':               sorted_state_list,
    }
    return render(request, 'organization/organization_edit.html', template_values)


@login_required
def organization_edit_view(request, organization_id=0, organization_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # A positive value in google_civic_election_id means we want to create a voter guide for this org for this election
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    organization_type = request.GET.get('organization_type', UNKNOWN)

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    organization_on_stage_found = False
    organization_manager = OrganizationManager()
    organization_on_stage = None
    state_served_code = ''
    new_issue_list = []
    results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)

    organization_twitter_handle = ""
    if results['organization_found']:
        organization_on_stage = results['organization']
        state_served_code = organization_on_stage.state_served_code
        organization_on_stage_found = True
        organization_we_vote_id = organization_on_stage.we_vote_id
        organization_twitter_handle = organization_on_stage.organization_twitter_handle
        issue_list_manager = IssueListManager()
        issue_list_results = issue_list_manager.retrieve_issues(ALPHABETICAL_ASCENDING, show_hidden_issues=True)
        if issue_list_results["issue_list_found"]:
            issue_list = issue_list_results["issue_list"]
            link_issue_list_manager = OrganizationLinkToIssueList()
            organization_issue_we_vote_id_list = link_issue_list_manager. \
                fetch_issue_we_vote_id_list_by_organization_we_vote_id(organization_on_stage.we_vote_id)

            for issue in issue_list:
                if issue.we_vote_id in organization_issue_we_vote_id_list:
                    issue.followed_by_organization = True
                else:
                    issue.followed_by_organization = False
                new_issue_list.append(issue)

    twitter_link_to_organization = None
    twitter_link_to_organization_handle = ""
    twitter_handle_mismatch = False
    if organization_on_stage_found:
        # TwitterLinkToOrganization
        twitter_user_manager = TwitterUserManager()
        results = twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization_we_vote_id)
        if results['twitter_link_to_organization_found']:
            twitter_link_to_organization = results['twitter_link_to_organization']
            twitter_link_to_organization_handle = \
                twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()
            if twitter_link_to_organization_handle and organization_twitter_handle:
                if twitter_link_to_organization_handle.lower() != organization_twitter_handle.lower():
                    twitter_handle_mismatch = True

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    organization_types_map = ORGANIZATION_TYPE_MAP
    # Sort by organization_type value (instead of key)
    organization_types_list = sorted(organization_types_map.items(), key=operator.itemgetter(1))

    voter_device_id = get_voter_api_device_id(request)
    voter = fetch_voter_from_voter_device_link(voter_device_id)
    if hasattr(voter, 'is_admin') and voter.is_admin:
        queryset = OrganizationChangeLog.objects.using('readonly').all()
        queryset = queryset.filter(organization_we_vote_id__iexact=organization_we_vote_id)
        queryset = queryset.order_by('-log_datetime')
        change_log_list = list(queryset)
    else:
        change_log_list = []

    template_values = {
        'change_log_list':                      change_log_list,
        'google_civic_election_id':             google_civic_election_id,
        'issue_list':                           new_issue_list,
        'messages_on_stage':                    messages_on_stage,
        'organization':                         organization_on_stage,
        'organization_types':                   organization_types_list,
        'state_list':                           sorted_state_list,
        'state_served_code':                    state_served_code,
        'twitter_handle_mismatch':              twitter_handle_mismatch,
        'twitter_link_to_organization':         twitter_link_to_organization,
        'twitter_link_to_organization_handle':  twitter_link_to_organization_handle,
        'upcoming_election_list':               upcoming_election_list,
        'voter':                                voter,
    }
    return render(request, 'organization/organization_edit.html', template_values)


@login_required
def organization_edit_account_view(request, organization_id=0, organization_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # A positive value in google_civic_election_id means we want to create a voter guide for this org for this election
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    organization_type = request.GET.get('organization_type', UNKNOWN)

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    organization_on_stage_found = False
    organization_manager = OrganizationManager()
    organization_on_stage = Organization()
    state_served_code = ''
    new_issue_list = []
    results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)

    if results['organization_found']:
        organization_on_stage = results['organization']
        state_served_code = organization_on_stage.state_served_code
        organization_on_stage_found = True
        issue_list_manager = IssueListManager()
        issue_list_results = issue_list_manager.retrieve_issues(ALPHABETICAL_ASCENDING, show_hidden_issues=True)
        if issue_list_results["issue_list_found"]:
            issue_list = issue_list_results["issue_list"]
            link_issue_list_manager = OrganizationLinkToIssueList()
            organization_issue_we_vote_id_list = link_issue_list_manager. \
                fetch_issue_we_vote_id_list_by_organization_we_vote_id(organization_on_stage.we_vote_id)

            for issue in issue_list:
                if issue.we_vote_id in organization_issue_we_vote_id_list:
                    issue.followed_by_organization = True
                else:
                    issue.followed_by_organization = False
                new_issue_list.append(issue)

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    master_feature_package_query = MasterFeaturePackage.objects.all()
    master_feature_package_list = list(master_feature_package_query)

    organization_types_map = ORGANIZATION_TYPE_MAP
    # Sort by organization_type value (instead of key)
    organization_types_list = sorted(organization_types_map.items(), key=operator.itemgetter(1))

    on_development_server = 'localhost' in WE_VOTE_SERVER_ROOT_URL
    if organization_on_stage_found:
        template_values = {
            'google_civic_election_id': google_civic_election_id,
            'issue_list':               new_issue_list,
            'master_feature_package_list': master_feature_package_list,
            'messages_on_stage':        messages_on_stage,
            'on_development_server':    on_development_server,
            'organization':             organization_on_stage,
            'organization_types':       organization_types_list,
            'state_list':               sorted_state_list,
            'state_served_code':        state_served_code,
            'upcoming_election_list':   upcoming_election_list,
        }
    else:
        template_values = {
            'google_civic_election_id': google_civic_election_id,
            'issue_list':               new_issue_list,
            'master_feature_package_list': master_feature_package_list,
            'messages_on_stage':        messages_on_stage,
            'on_development_server':    on_development_server,
            'state_list':               sorted_state_list,
            'upcoming_election_list':   upcoming_election_list,
        }
    return render(request, 'organization/organization_edit_account.html', template_values)


@login_required
def organization_edit_listed_campaigns_view(request, organization_id=0, organization_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    organization_manager = OrganizationManager()
    organization_on_stage = Organization()
    results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)

    if results['organization_found']:
        organization_on_stage = results['organization']
        organization_we_vote_id = organization_on_stage.we_vote_id

    campaignx_manager = CampaignXManager()
    campaignx_listed_by_organization_list_modified = []
    campaignx_listed_by_organization_list = campaignx_manager.retrieve_campaignx_listed_by_organization_list(
        site_owner_organization_we_vote_id=organization_we_vote_id,
        ignore_visible_to_public=True
    )

    voter_manager = VoterManager()
    for campaignx_listed_by_organization in campaignx_listed_by_organization_list:
        if positive_value_exists(campaignx_listed_by_organization.campaignx_we_vote_id):
            results = campaignx_manager.retrieve_campaignx(
                campaignx_we_vote_id=campaignx_listed_by_organization.campaignx_we_vote_id)
            if results['campaignx_found']:
                campaignx_listed_by_organization.campaign_title = results['campaignx'].campaign_title
        if positive_value_exists(campaignx_listed_by_organization.listing_requested_by_voter_we_vote_id):
            results = voter_manager.retrieve_voter_by_we_vote_id(
                campaignx_listed_by_organization.listing_requested_by_voter_we_vote_id,
                read_only=True)
            if results['voter_found']:
                campaignx_listed_by_organization.listing_requested_by_voter_name = results['voter'].get_full_name()

        campaignx_listed_by_organization_list_modified.append(campaignx_listed_by_organization)

    template_values = {
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'organization':             organization_on_stage,
        'state_code':               state_code,
        'campaignx_listed_by_organization_list':    campaignx_listed_by_organization_list_modified,
    }
    return render(request, 'organization/organization_edit_listed_campaigns.html', template_values)


@login_required
def organization_delete_process_view(request):
    """
    Delete an organization
    :param request:
    :return:
    """
    status = ""
    organization_id = convert_to_int(request.POST.get('organization_id', 0))
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))

    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this organization. '
                             'Please check the checkbox to confirm you want to delete this organization.')
        return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id)
    if results['organization_found']:
        organization = results['organization']

        organization_link_to_issue_list = OrganizationLinkToIssueList()
        link_list = organization_link_to_issue_list.retrieve_issue_list_by_organization_we_vote_id(
            organization_we_vote_id=organization.we_vote_id,
            show_hidden_issues=True,
            read_only=False)
        link_to_issue_could_not_be_deleted = False
        if len(link_list) > 0:
            for one_link in link_list:
                try:
                    one_link.delete()
                except Exception as e:
                    link_to_issue_could_not_be_deleted = True
                    status += "COULD_NOT_DELETE_LINK: " + str(e) + " "

        if positive_value_exists(link_to_issue_could_not_be_deleted):
            messages.add_message(request, messages.ERROR,
                                 status +
                                 'Could not delete -- issues still attached to this organization.')
            return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))

        organization_we_vote_id = organization.we_vote_id

        # Delete the TwitterLinkToOrganization
        twitter_user_manager = TwitterUserManager()
        twitter_id = 0
        results = twitter_user_manager.delete_twitter_link_to_organization(twitter_id, organization_we_vote_id)
        if not positive_value_exists(results['twitter_link_to_organization_deleted']) \
                and not positive_value_exists(results['twitter_link_to_organization_not_found']):
            status += results['status']
            messages.add_message(request, messages.ERROR, 'Could not delete TwitterLinkToOrganization: {status}'
                                                          ''.format(status=status))
            return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))

        organization.delete()
        messages.add_message(request, messages.INFO, 'Endorser deleted.')
    else:
        messages.add_message(request, messages.ERROR, 'Endorser not found.')

    return HttpResponseRedirect(reverse('organization:organization_list', args=()))


@login_required
def organization_edit_process_view(request):
    """
    Process the new or edit organization forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ''
    success = True
    voter_device_id = get_voter_api_device_id(request)
    voter = fetch_voter_from_voter_device_link(voter_device_id)
    change_description = ''
    if hasattr(voter, 'last_name'):
        changed_by_name = voter.get_full_name()
        changed_by_voter_we_vote_id = voter.we_vote_id
    else:
        changed_by_name = ""
        changed_by_voter_we_vote_id = ''

    issue_analysis_admin_notes = request.POST.get('issue_analysis_admin_notes', False)
    issue_analysis_done = request.POST.get('issue_analysis_done', False)
    organization_contact_form_url = request.POST.get('organization_contact_form_url', False)
    organization_email = request.POST.get('organization_email', False)
    organization_endorsements_api_url = request.POST.get('organization_endorsements_api_url', False)
    organization_facebook = request.POST.get('organization_facebook', False)
    organization_id = convert_to_int(request.POST.get('organization_id', 0))
    organization_instagram_handle = request.POST.get('organization_instagram_handle', False)
    organization_link_issue_we_vote_ids = request.POST.getlist('selected_issues', False)
    organization_name = request.POST.get('organization_name', '')
    try:
        organization_photo_file = request.FILES['organization_photo_file']
        organization_photo_file_found = True
    except Exception as e:
        organization_photo_file = None
        organization_photo_file_found = False
    organization_photo_file_delete = positive_value_exists(request.POST.get('organization_photo_file_delete', False))
    organization_twitter_handle = request.POST.get('organization_twitter_handle', False)
    organization_twitter_updates_failing = \
        positive_value_exists(request.POST.get('organization_twitter_updates_failing', False))
    organization_type = request.POST.get('organization_type', GROUP)
    organization_website = request.POST.get('organization_website', False)
    profile_image_type_currently_active = request.POST.get('profile_image_type_currently_active', False)
    state_served_code = request.POST.get('state_served_code', False)
    wikipedia_page_title = request.POST.get('wikipedia_page_title', False)
    wikipedia_photo_url = request.POST.get('wikipedia_photo_url', False)

    # A positive value in google_civic_election_id or add_organization_button means we want to create a voter guide
    # for this org for this election
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    election_manager = ElectionManager()
    current_organization_with_new_twitter_handle = False

    # Have a version of state_code that is "" instead of False
    if positive_value_exists(state_served_code):
        state_code = state_served_code
    else:
        state_code = ""

    # Filter incoming data
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle)
    organization_instagram_handle = extract_instagram_handle_from_text_string(organization_instagram_handle)

    # Check to see if this organization is already being used anywhere
    organization_on_stage = None
    organization_on_stage_found = False
    organization_we_vote_id = ""
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if organization_query.count():
            organization_on_stage = organization_query[0]
            organization_on_stage_found = True
            organization_we_vote_id = organization_on_stage.we_vote_id
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        status += "ORGANIZATION_COULD_NOT_BE_RETRIEVED: " + str(e) + " "
        success = False

    # We can use the same url_variables with any processing failures below

    url_variables = "?n=1"

    if issue_analysis_admin_notes is not False:
        url_variables += "&issue_analysis_admin_notes=" + str(issue_analysis_admin_notes)

    if issue_analysis_done is not False:
        url_variables += "&issue_analysis_done=" + str(issue_analysis_done)

    if organization_contact_form_url is not False:
        url_variables += "&organization_contact_form_url=" + str(organization_contact_form_url)
    
    if organization_email is not False:
        url_variables += "&organization_email=" + str(organization_email)

    if organization_endorsements_api_url is not False:
        url_variables += "&organization_endorsements_api_url=" + str(organization_endorsements_api_url)

    if organization_facebook is not False:
        url_variables += "&organization_facebook=" + str(organization_facebook)

    if  organization_id is not False:
        url_variables += "&organization_id=" + str(organization_id)

    if organization_instagram_handle is not False:
        url_variables += "&organization_instagram_handle=" + str(organization_instagram_handle)

    if organization_name is not False:
        url_variables += "&organization_name=" + str(organization_name)

    if organization_twitter_handle is not False:
        url_variables += "&organization_twitter_handle=" + str(organization_twitter_handle)

    if organization_twitter_updates_failing is not False:
        url_variables += "&organization_twitter_updates_failing=" + str(organization_twitter_updates_failing)

    if organization_type is not False:
        url_variables += "&organization_type=" + str(organization_type)

    if organization_website is not False:
        url_variables += "&organization_website=" + str(organization_website)

    if profile_image_type_currently_active is not False:
        url_variables += "&profile_image_type_currently_active=" + str(profile_image_type_currently_active)

    if state_served_code is not False:
        url_variables += "&state_served_code=" + str(state_served_code)

    if wikipedia_page_title is not False:
        url_variables += "&wikipedia_page_title=" + str(wikipedia_page_title)

    if wikipedia_photo_url is not False:
        url_variables += "&wikipedia_photo_url=" + str(wikipedia_photo_url)

    if google_civic_election_id is not False:
        url_variables += "&google_civic_election_id=" + str(google_civic_election_id)
    

    if not success:
        messages.add_message(request, messages.ERROR,
                             'ORGANIZATION_ERROR Please click the back arrow and send URL to the engineering team: '
                             '' + str(status))
        return HttpResponseRedirect(reverse('organization:organization_list', args=()) + url_variables)

    twitter_user_manager = TwitterUserManager()
    create_twitter_link_to_organization_for_handle = False
    preserve_twitter_link_to_organization_if_twitter_id = 0
    twitter_link_to_organization_from_handle_twitter_id = 0
    twitter_handle_can_be_saved_without_conflict = True
    if not positive_value_exists(organization_twitter_handle):
        # Delete TwitterLinkToOrganization
        delete_results = twitter_user_manager.delete_twitter_link_to_organization(
            twitter_id=0,
            organization_we_vote_id=organization_we_vote_id)
        if not delete_results['success']:
            messages.add_message(request, messages.ERROR, 'Could not delete TwitterLinkToOrganization 1.')
    elif organization_on_stage and organization_twitter_handle != organization_on_stage.organization_twitter_handle:
        # Delete existing TwitterLinkToOrganization since we are switching to a different twitter handle
        delete_results = twitter_user_manager.delete_twitter_link_to_organization(
            twitter_id=0,
            organization_we_vote_id=organization_we_vote_id)
        if not delete_results['success']:
            messages.add_message(request, messages.ERROR, 'Could not delete TwitterLinkToOrganization 2.')

    if positive_value_exists(organization_twitter_handle):
        # Check to see if there is a TwitterLinkToOrganization entry tied to this twitter_handle
        link_results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
            twitter_handle=organization_twitter_handle)
        # 12/15/21 Steve: This one is weird, since success usually just means that nothing crashed
        if not link_results['success']:
            messages.add_message(request, messages.ERROR,
                                 'Could not retrieve TwitterLinkToOrganization by handle: ' + link_results['status'])
            twitter_handle_can_be_saved_without_conflict = False
        elif link_results['twitter_link_to_organization_found']:
            twitter_link_to_organization_from_handle = link_results['twitter_link_to_organization']
            if twitter_link_to_organization_from_handle.organization_we_vote_id == organization_we_vote_id:
                preserve_twitter_link_to_organization_if_twitter_id = \
                    twitter_link_to_organization_from_handle.twitter_id
            else:
                twitter_handle_can_be_saved_without_conflict = False
                messages.add_message(
                    request, messages.ERROR,
                    'Twitter handle already linked to another organization. Twitter handle not saved/changed.')
        else:
            # If not found, then make note that we can create a TwitterLinkToOrganization
            create_twitter_link_to_organization_for_handle = True
            results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                twitter_handle=organization_twitter_handle)
            if not results['success']:
                messages.add_message(request, messages.ERROR, 'Could not retrieve TwitterUser by handle.')
                twitter_handle_can_be_saved_without_conflict = False
            elif results['twitter_user_found']:
                twitter_user = results['twitter_user']
                twitter_link_to_organization_from_handle_twitter_id = twitter_user.twitter_id
            else:
                messages.add_message(request, messages.ERROR, 'Twitter handle you entered not found on Twitter.')
                twitter_handle_can_be_saved_without_conflict = False

    if positive_value_exists(organization_we_vote_id) and twitter_handle_can_be_saved_without_conflict:
        # Check to see if there is a TwitterLinkToOrganization entry tied to this organization_we_vote_id
        link_results = twitter_user_manager.retrieve_twitter_link_to_organization(
            organization_we_vote_id=organization_we_vote_id)
        if not link_results['success']:
            messages.add_message(request, messages.ERROR, 'Could not retrieve TwitterLinkToOrganization by we_vote_id.')
            twitter_handle_can_be_saved_without_conflict = False
        elif link_results['twitter_link_to_organization_found']:
            twitter_link_to_organization_from_org = link_results['twitter_link_to_organization']
            if twitter_link_to_organization_from_org.twitter_id == preserve_twitter_link_to_organization_if_twitter_id:
                # Is the same so do not delete
                pass
            else:
                # Delete TwitterLinkToOrganization
                delete_results = twitter_user_manager.delete_twitter_link_to_organization(
                    twitter_id=0,
                    organization_we_vote_id=organization_we_vote_id)
                if not delete_results['success']:
                    messages.add_message(request, messages.ERROR, 'Could not delete TwitterLinkToOrganization 3.')

    if not positive_value_exists(organization_we_vote_id):
        organization_manager = OrganizationManager()
        org_results = organization_manager.update_or_create_organization(
            organization_id='',
            we_vote_id='',
            organization_website_search='',
            organization_twitter_search='',
            organization_name=organization_name,
            organization_website=organization_website,
            organization_email=organization_email,
            organization_facebook=organization_facebook,
            organization_type=organization_type,
            profile_image_type_currently_active=profile_image_type_currently_active,
        )
        if not org_results['success']:
            status += "CREATE_OR_UPDATE_ORGANIZATION_FAILED: " + str(org_results['status']) + " "
            messages.add_message(request, messages.ERROR,
                                 'ORGANIZATION_ERROR Please click the back arrow and send URL to the engineering team: '
                                 '' + str(status))
            return HttpResponseRedirect(reverse('organization:organization_list', args=()) + url_variables)
        else:
            organization_on_stage_found = True
            organization_on_stage = org_results['organization']
            org_results_organization_we_vote_id = organization_on_stage.we_vote_id
            if twitter_handle_can_be_saved_without_conflict and create_twitter_link_to_organization_for_handle \
                    and positive_value_exists(twitter_link_to_organization_from_handle_twitter_id):
                create_results = twitter_user_manager.create_twitter_link_to_organization(
                    twitter_id=twitter_link_to_organization_from_handle_twitter_id,
                    organization_we_vote_id=organization_we_vote_id
                    if positive_value_exists(organization_we_vote_id) else org_results_organization_we_vote_id)
                if not create_results['success']:
                    messages.add_message(request, messages.ERROR, 'Could not create TwitterLinkToOrganization.')
                    twitter_handle_can_be_saved_without_conflict = False

    issue_analysis_done_changed = False
    try:
        if organization_on_stage_found:
            # Update below
            organization_id = organization_on_stage.id
            organization_we_vote_id = organization_on_stage.we_vote_id
            status += "ORG_UPDATING "

            messages.add_message(request, messages.INFO, 'Endorser updating.')
        else:
            # Create new
            # But first double-check that we don't have an org entry already
            organization_email = ''
            organization_list_manager = OrganizationListManager()
            results = organization_list_manager.organization_search_find_any_possibilities(
                organization_name, organization_twitter_handle, organization_website, organization_email)

            if results['organizations_found']:
                organizations_list = results['organizations_list']
                organizations_count = len(organizations_list)

                upcoming_election_list = []
                results = election_manager.retrieve_upcoming_elections()
                if results['success']:
                    upcoming_election_list = results['election_list']

                state_list = STATE_CODE_MAP
                sorted_state_list = sorted(state_list.items())

                messages.add_message(request, messages.INFO, 'We found {count} existing organizations '
                                                             'that might match.'.format(count=organizations_count))
                messages_on_stage = get_messages(request)
                template_values = {
                    'google_civic_election_id':     google_civic_election_id,
                    'messages_on_stage':            messages_on_stage,
                    'organizations_list':           organizations_list,
                    'organization_name':            organization_name,
                    'organization_instagram_handle':    organization_instagram_handle,
                    'organization_twitter_handle':  organization_twitter_handle,
                    'organization_facebook':        organization_facebook,
                    'organization_website':         organization_website,
                    'wikipedia_page_title':         wikipedia_page_title,
                    'wikipedia_photo_url':          wikipedia_photo_url,
                    'state_served_code':            state_served_code,
                    'state_list':                   sorted_state_list,
                    'upcoming_election_list':       upcoming_election_list,
                }
                return render(request, 'voter_guide/voter_guide_search.html', template_values)

            minimum_required_variables_exist = positive_value_exists(organization_name)
            if not minimum_required_variables_exist:
                upcoming_election_list = []
                results = election_manager.retrieve_upcoming_elections()
                if results['success']:
                    upcoming_election_list = results['election_list']

                state_list = STATE_CODE_MAP
                sorted_state_list = sorted(state_list.items())

                messages.add_message(request, messages.INFO, 'Missing organization_name, which is required.')
                messages_on_stage = get_messages(request)
                template_values = {
                    'google_civic_election_id':     google_civic_election_id,
                    'messages_on_stage':            messages_on_stage,
                    'organization_instagram_handle':    organization_instagram_handle,
                    'organization_name':            organization_name,
                    'organization_twitter_handle':  organization_twitter_handle,
                    'organization_facebook':        organization_facebook,
                    'organization_website':         organization_website,
                    'wikipedia_page_title':         wikipedia_page_title,
                    'wikipedia_photo_url':          wikipedia_photo_url,
                    'state_served_code':            state_served_code,
                    'state_list':                   sorted_state_list,
                    'upcoming_election_list':       upcoming_election_list,
                }
                return render(request, 'voter_guide/voter_guide_search.html', template_values)

            organization_on_stage = Organization(
                organization_name=organization_name,
            )
            organization_on_stage_found = True
            organization_id = organization_on_stage.id
            organization_we_vote_id = organization_on_stage.we_vote_id
            status += "ORG_CREATED "
            messages.add_message(request, messages.INFO, 'New organization created.')

        if organization_on_stage_found:
            # #################################################
            # Process incoming uploaded photo if there is one
            organization_photo_in_binary_format = None
            organization_photo_converted_to_binary = False
            if organization_photo_file_found:
                try:
                    organization_photo_in_binary_format = b64encode(organization_photo_file.read()).decode('utf-8')
                    organization_photo_converted_to_binary = True
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         "Error converting organization photo to binary: {error}".format(error=e))
            if organization_photo_file_found and organization_photo_converted_to_binary:
                photo_results = organization_save_photo_from_file_reader(
                    organization_we_vote_id=organization_we_vote_id,
                    organization_photo_binary_file=organization_photo_in_binary_format)
                if photo_results['we_vote_hosted_organization_photo_original_url']:
                    we_vote_hosted_organization_photo_original_url = \
                        photo_results['we_vote_hosted_organization_photo_original_url']
                    # Now we want to resize to a large version
                    create_resized_image_results = create_resized_images(
                        organization_we_vote_id=organization_we_vote_id,
                        organization_uploaded_profile_image_url_https=we_vote_hosted_organization_photo_original_url)
                    organization_on_stage.we_vote_hosted_profile_uploaded_image_url_large = \
                        create_resized_image_results['cached_resized_image_url_large']
                    organization_on_stage.we_vote_hosted_profile_uploaded_image_url_medium = \
                        create_resized_image_results['cached_resized_image_url_medium']
                    organization_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny = \
                        create_resized_image_results['cached_resized_image_url_tiny']
                    if profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN \
                            or profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UPLOADED:
                        organization_on_stage.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UPLOADED
                        organization_on_stage.we_vote_hosted_profile_image_url_large = \
                            organization_on_stage.we_vote_hosted_profile_uploaded_image_url_large
                        organization_on_stage.we_vote_hosted_profile_image_url_medium = \
                            organization_on_stage.we_vote_hosted_profile_uploaded_image_url_medium
                        organization_on_stage.we_vote_hosted_profile_image_url_tiny = \
                            organization_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny
                    elif profile_image_type_currently_active is not False:
                        organization_on_stage.profile_image_type_currently_active = profile_image_type_currently_active
            elif organization_photo_file_delete:
                organization_on_stage.we_vote_hosted_profile_uploaded_image_url_large = None
                organization_on_stage.we_vote_hosted_profile_uploaded_image_url_medium = None
                organization_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny = None
                if profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UPLOADED \
                        or profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                    organization_on_stage.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UNKNOWN
                    organization_on_stage.we_vote_hosted_profile_image_url_large = None
                    organization_on_stage.we_vote_hosted_profile_image_url_medium = None
                    organization_on_stage.we_vote_hosted_profile_image_url_tiny = None
            elif profile_image_type_currently_active is not False:
                from image.controllers import organize_object_photo_fields_based_on_image_type_currently_active
                results = organize_object_photo_fields_based_on_image_type_currently_active(
                    object_with_photo_fields=organization_on_stage,
                    profile_image_type_currently_active=profile_image_type_currently_active,
                )
                if results['success']:
                    organization_on_stage = results['object_with_photo_fields']

            # ###############################################
            # Now process all other organization fields
            if issue_analysis_admin_notes is not False:
                organization_on_stage.issue_analysis_admin_notes = issue_analysis_admin_notes.strip()
            issue_analysis_done_before = positive_value_exists(organization_on_stage.issue_analysis_done)
            if issue_analysis_done_before is not positive_value_exists(issue_analysis_done):
                issue_analysis_done_changed = True
            organization_on_stage.issue_analysis_done = positive_value_exists(issue_analysis_done)
            if organization_twitter_handle is not False:
                if twitter_handle_can_be_saved_without_conflict:
                    organization_on_stage.organization_twitter_handle = organization_twitter_handle
                organization_on_stage.organization_twitter_updates_failing = organization_twitter_updates_failing
            if organization_contact_form_url is not False:
                organization_on_stage.organization_contact_form_url = organization_contact_form_url.strip()
            if organization_email is not False:
                organization_on_stage.organization_email = organization_email.strip() if organization_email else None
            if organization_endorsements_api_url is not False:
                organization_on_stage.organization_endorsements_api_url = organization_endorsements_api_url.strip() \
                    if organization_endorsements_api_url else None
            if organization_facebook is not False:
                organization_on_stage.organization_facebook = organization_facebook.strip() \
                    if organization_facebook else None
            if organization_instagram_handle is not False:
                organization_on_stage.organization_instagram_handle = organization_instagram_handle.strip() \
                    if organization_instagram_handle else None
            if organization_name is not False:
                organization_on_stage.organization_name = organization_name.strip() if organization_name else None
            if organization_type is not False:
                organization_on_stage.organization_type = organization_type.strip() if organization_type else UNKNOWN
            if organization_website is not False:
                organization_on_stage.organization_website = organization_website.strip() \
                    if organization_website else None
            if state_served_code is not False:
                organization_on_stage.state_served_code = state_served_code.strip() if state_served_code else None
            if wikipedia_page_title is not False:
                organization_on_stage.wikipedia_page_title = wikipedia_page_title.strip() \
                    if wikipedia_page_title else None
            if wikipedia_photo_url is not False:
                organization_on_stage.wikipedia_photo_url = wikipedia_photo_url.strip() if wikipedia_photo_url else None
            organization_on_stage.save()
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save organization.'
                                                      ' {error} [type: {error_type}]'.format(error=e,
                                                                                             error_type=type(e)))
        return HttpResponseRedirect(reverse('organization:organization_list', args=()))

    # Pull the latest Twitter information
    if not organization_twitter_updates_failing and not organization_on_stage.organization_twitter_updates_failing:
        results = refresh_twitter_organization_details(organization_on_stage)
        status += results['status']

    if positive_value_exists(organization_we_vote_id):
        push_organization_data_to_other_table_caches(organization_we_vote_id)

    # Voter guide names are currently locked to the organization name, so we want to update all voter guides
    voter_guide_manager = VoterGuideManager()
    results = voter_guide_manager.update_organization_voter_guides_with_organization_data(organization_on_stage)
    if not results['success']:
        status += results['status']
        messages.add_message(request, messages.ERROR, 'VOTER_GUIDE_UPDATE_FAILED: ' + status)

    # Create voter_guide for this election?
    if positive_value_exists(google_civic_election_id) and positive_value_exists(organization_we_vote_id):
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']

            voter_guide_we_vote_id = ''
            results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                voter_guide_we_vote_id, organization_we_vote_id, google_civic_election_id, state_code)
            if results['voter_guide_saved']:
                messages.add_message(request, messages.INFO, 'Voter guide for {election_name} election saved.'
                                                             ''.format(election_name=election.election_name))

    # Link the selected issues with organization and delete any links that were unselected
    link_issue_list_manager = OrganizationLinkToIssueList()
    link_issue_manager = OrganizationLinkToIssueManager()
    issue_id = 0

    organization_follow_issues_we_vote_id_list_prior_to_update = link_issue_list_manager.\
        fetch_issue_we_vote_id_list_by_organization_we_vote_id(organization_we_vote_id)

    if positive_value_exists(organization_link_issue_we_vote_ids):
        # If here we have a complete list of issues that the organization should be linked to
        for issue_we_vote_id in organization_link_issue_we_vote_ids:
            if issue_we_vote_id in organization_follow_issues_we_vote_id_list_prior_to_update:
                organization_follow_issues_we_vote_id_list_prior_to_update.remove(issue_we_vote_id)
            else:
                # If here, this is a new issue link
                link_issue_manager.link_organization_to_issue(organization_we_vote_id, issue_id, issue_we_vote_id)
                link_issue_changed = True
                change_description += "{issue_we_vote_id} ADD ".format(issue_we_vote_id=issue_we_vote_id)
    # this check necessary when, organization has issues linked previously, but all the
    # issues are unchecked
    if positive_value_exists(organization_follow_issues_we_vote_id_list_prior_to_update):
        # If a previously linked issue was NOT on the complete list of issues taken in above, unlink those issues
        for issue_we_vote_id in organization_follow_issues_we_vote_id_list_prior_to_update:
            link_issue_manager.unlink_organization_to_issue(organization_we_vote_id, issue_id, issue_we_vote_id)
            change_description += "{issue_we_vote_id} REMOVE ".format(issue_we_vote_id=issue_we_vote_id)
    if issue_analysis_done_changed:
        if issue_analysis_done:
            change_description += "CHANGED: ANALYSIS_DONE "
        else:
            change_description += "CHANGED: ANALYSIS_NOT_DONE "

    position_list_manager = PositionListManager()
    position_list_manager.refresh_cached_position_info_for_organization(organization_we_vote_id)

    if positive_value_exists(change_description):
        OrganizationChangeLog.objects.create(
            change_description=change_description,
            changed_by_name=changed_by_name,
            changed_by_voter_we_vote_id=changed_by_voter_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            status=status,
        )

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) + "&state_code=" +
                                str(state_code))


@login_required
def organization_edit_account_process_view(request):
    """
    Process the edit organization account forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_id = convert_to_int(request.POST.get('organization_id', 0))
    chosen_about_organization_external_url = request.POST.get('chosen_about_organization_external_url', None)
    chosen_domain_string = request.POST.get('chosen_domain_string', None)
    chosen_domain_string2 = request.POST.get('chosen_domain_string2', None)
    chosen_domain_string3 = request.POST.get('chosen_domain_string3', None)
    chosen_domain_type_is_campaign = request.POST.get('chosen_domain_type_is_campaign', None)
    chosen_favicon_url_https = request.POST.get('chosen_favicon_url_https', None)
    chosen_google_analytics_tracking_id = request.POST.get('chosen_google_analytics_tracking_id', None)
    chosen_html_verification_string = request.POST.get('chosen_html_verification_string', None)
    chosen_hide_we_vote_logo = request.POST.get('chosen_hide_we_vote_logo', None)
    chosen_logo_url_https = request.POST.get('chosen_logo_url_https', None)
    chosen_organization_api_pass_code = request.POST.get('chosen_organization_api_pass_code', None)
    chosen_prevent_sharing_opinions = request.POST.get('chosen_prevent_sharing_opinions', None)
    chosen_ready_introduction_text = request.POST.get('chosen_ready_introduction_text', None)
    chosen_ready_introduction_title = request.POST.get('chosen_ready_introduction_title', None)
    chosen_social_share_description = request.POST.get('chosen_social_share_description', None)
    chosen_social_share_image_256x256_url_https = request.POST.get('chosen_social_share_image_256x256_url_https', None)
    chosen_subdomain_string = request.POST.get('chosen_subdomain_string', None)
    chosen_website_name = request.POST.get('chosen_website_name', None)
    chosen_feature_package = request.POST.get('chosen_feature_package', None)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', None)

    # Check to see if this organization is already being used anywhere
    organization_on_stage = None
    organization_on_stage_found = False
    chosen_subdomain_string_allowed = False
    chosen_subdomain_string_previous = ''
    status = ""

    try:
        organization_on_stage = Organization.objects.get(id=organization_id)
        organization_on_stage_found = True
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Account settings can only be edited on existing organization.')
        status += "EDIT_ACCOUNT_PROCESS_ORGANIZATION_NOT_FOUND "

    try:
        if organization_on_stage_found:
            chosen_subdomain_string_previous = organization_on_stage.chosen_subdomain_string

            # Update
            if chosen_about_organization_external_url is not None:
                organization_on_stage.chosen_about_organization_external_url = \
                    chosen_about_organization_external_url.strip()
            if chosen_domain_string is not None:
                if positive_value_exists(chosen_domain_string):
                    domain_results = full_domain_string_available(chosen_domain_string,
                                                                  requesting_organization_id=organization_id)
                    if domain_results['full_domain_string_available']:
                        organization_on_stage.chosen_domain_string = chosen_domain_string.strip()
                    else:
                        message = 'Cannot save full domain: \'' + chosen_domain_string + '\', status: ' + \
                                  domain_results['status']
                        messages.add_message(request, messages.ERROR, message)
                        status += domain_results['status']
                else:
                    organization_on_stage.chosen_domain_string = None
            if chosen_domain_string2 is not None:
                if positive_value_exists(chosen_domain_string2):
                    domain_results = full_domain_string_available(chosen_domain_string2,
                                                                  requesting_organization_id=organization_id)
                    if domain_results['full_domain_string_available']:
                        organization_on_stage.chosen_domain_string2 = chosen_domain_string2.strip()
                    else:
                        message = 'Cannot save chosen_domain_string2: \'' + chosen_domain_string2 + '\', status: ' + \
                                  domain_results['status']
                        messages.add_message(request, messages.ERROR, message)
                        status += domain_results['status']
                else:
                    organization_on_stage.chosen_domain_string2 = None
            if chosen_domain_string3 is not None:
                if positive_value_exists(chosen_domain_string3):
                    domain_results = full_domain_string_available(chosen_domain_string3,
                                                                  requesting_organization_id=organization_id)
                    if domain_results['full_domain_string_available']:
                        organization_on_stage.chosen_domain_string3 = chosen_domain_string3.strip()
                    else:
                        message = 'Cannot save chosen_domain_string3: \'' + chosen_domain_string3 + '\', status: ' + \
                                  domain_results['status']
                        messages.add_message(request, messages.ERROR, message)
                        status += domain_results['status']
                else:
                    organization_on_stage.chosen_domain_string3 = None
            if chosen_domain_type_is_campaign is not None:
                organization_on_stage.chosen_domain_type_is_campaign = chosen_domain_type_is_campaign
            if chosen_favicon_url_https is not None:
                organization_on_stage.chosen_favicon_url_https = chosen_favicon_url_https
            if chosen_google_analytics_tracking_id is not None:
                organization_on_stage.chosen_google_analytics_tracking_id = \
                    chosen_google_analytics_tracking_id.strip()
            if chosen_html_verification_string is not None:
                organization_on_stage.chosen_html_verification_string = chosen_html_verification_string.strip()
            if chosen_hide_we_vote_logo is not None:
                organization_on_stage.chosen_hide_we_vote_logo = positive_value_exists(chosen_hide_we_vote_logo)
            if chosen_logo_url_https is not None:
                organization_on_stage.chosen_logo_url_https = chosen_logo_url_https.strip()
            if chosen_organization_api_pass_code is not None:
                organization_on_stage.chosen_organization_api_pass_code = chosen_organization_api_pass_code.strip()
            if chosen_prevent_sharing_opinions is not None:
                organization_on_stage.chosen_prevent_sharing_opinions \
                    = positive_value_exists(chosen_prevent_sharing_opinions)
            if chosen_ready_introduction_text is not None:
                organization_on_stage.chosen_ready_introduction_text = chosen_ready_introduction_text
            if chosen_ready_introduction_title is not None:
                organization_on_stage.chosen_ready_introduction_title = chosen_ready_introduction_title
            if chosen_social_share_description is not None:
                organization_on_stage.chosen_social_share_description = chosen_social_share_description.strip()
            if chosen_social_share_image_256x256_url_https is not None:
                organization_on_stage.chosen_social_share_image_256x256_url_https = \
                    chosen_social_share_image_256x256_url_https.strip()
            if chosen_subdomain_string is not None:
                if positive_value_exists(chosen_subdomain_string):
                    domain_results = subdomain_string_available(chosen_subdomain_string,
                                                                requesting_organization_id=organization_id)
                    if domain_results['subdomain_string_available']:
                        organization_on_stage.chosen_subdomain_string = chosen_subdomain_string.strip()
                        chosen_subdomain_string_allowed = True
                    else:
                        message = 'Cannot save sub domain: \'' + chosen_subdomain_string + '\', status: ' + \
                                  domain_results['status']
                        messages.add_message(request, messages.ERROR, message)
                        status += domain_results['status']
                else:
                    organization_on_stage.chosen_subdomain_string = None
            if chosen_website_name is not None:
                organization_on_stage.chosen_website_name = chosen_website_name.strip()
            if chosen_feature_package is not None:
                master_feature_package_query = MasterFeaturePackage.objects.all()
                master_feature_package_list = list(master_feature_package_query)
                for feature_package in master_feature_package_list:
                    if feature_package.master_feature_package == chosen_feature_package:
                        organization_on_stage.chosen_feature_package = chosen_feature_package
                        organization_on_stage.features_provided_bitmap = feature_package.features_provided_bitmap

            organization_on_stage.save()
            organization_id = organization_on_stage.id

            messages.add_message(request, messages.INFO, 'Endorser account information updated.')
        else:
            # We do not create organizations in this view
            pass
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save organization.'
                                                      ' {error} [type: {error_type}]'.format(error=e,
                                                                                             error_type=type(e)))

    # Now see about adding chosen_subdomain_string networking information
    if positive_value_exists(chosen_subdomain_string_allowed):
        on_development_server = 'localhost' in WE_VOTE_SERVER_ROOT_URL
        if on_development_server:
            status += "FASTLY_NOT_UPDATED-ON_DEVELOPMENT_SERVER: " + str(WE_VOTE_SERVER_ROOT_URL) + " "
        elif positive_value_exists(chosen_subdomain_string) or positive_value_exists(chosen_subdomain_string_previous):
            chosen_subdomain_has_changed = True
            if positive_value_exists(chosen_subdomain_string) and \
                    positive_value_exists(chosen_subdomain_string_previous):
                chosen_subdomain_has_changed = chosen_subdomain_string != chosen_subdomain_string_previous
            if not chosen_subdomain_has_changed:
                status += "SUBDOMAIN_HAS_NOT_CHANGED "
            elif positive_value_exists(chosen_subdomain_string):
                subdomain_results = get_wevote_subdomain_status(chosen_subdomain_string)
                status += subdomain_results['status']
                if not subdomain_results['success']:
                    status += "COULD_NOT_GET_SUBDOMAIN_STATUS "
                elif not positive_value_exists(subdomain_results['subdomain_exists']):
                    # If here, this is a new chosen_subdomain_string to add to our network
                    status += "NEW_CHOSEN_SUBDOMAIN_STRING_DOES_NOT_EXIST "
                    add_results = add_wevote_subdomain_to_fastly(chosen_subdomain_string)
                    status += add_results['status']
                else:
                    status += "CHOSEN_SUBDOMAIN_ALREADY_EXISTS "

                # add subdomain to aws route53 DNS
                route53_results = add_subdomain_route53_record(chosen_subdomain_string)
                if route53_results['success']:
                    status += "SUBDOMAIN_ROUTE53_ADDED "
                else:
                    status += route53_results['status']
                    status += "SUBDOMAIN_ROUTE53_NOT_ADDED "
            # We don't delete subdomain records from our DNS
            if positive_value_exists(chosen_subdomain_string_previous):
                if chosen_subdomain_string_previous is not chosen_subdomain_string:
                    # Any benefit to deleting prior subdomain from Fastly?
                    pass

    messages.add_message(request, messages.INFO, 'Processing Status: {status}'.format(status=status))

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def organization_edit_listed_campaigns_process_view(request):
    """
    Process the edit listed campaigns form
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_listed_by_organization_campaignx_we_vote_id = \
        request.POST.get('campaignx_listed_by_organization_campaignx_we_vote_id', None)
    if positive_value_exists(campaignx_listed_by_organization_campaignx_we_vote_id):
        campaignx_listed_by_organization_campaignx_we_vote_id = \
            campaignx_listed_by_organization_campaignx_we_vote_id.strip()
    campaignx_listed_by_organization_visible_to_public = \
        positive_value_exists(request.POST.get('campaignx_listed_by_organization_visible_to_public', False))
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    organization_id = convert_to_int(request.POST.get('organization_id', None))
    organization_we_vote_id = request.POST.get('organization_we_vote_id', None)
    state_code = request.POST.get('state_code', '')

    # Create new CampaignXListedByOrganization
    if positive_value_exists(campaignx_listed_by_organization_campaignx_we_vote_id):
        if 'camp' not in campaignx_listed_by_organization_campaignx_we_vote_id:
            messages.add_message(request, messages.ERROR, 'Valid CampaignXWeVoteId missing.')
        else:
            do_not_create = False
            link_already_exists = False
            status = ""
            # Does it already exist?
            try:
                CampaignXListedByOrganization.objects.get(
                    campaignx_we_vote_id=campaignx_listed_by_organization_campaignx_we_vote_id,
                    site_owner_organization_we_vote_id=organization_we_vote_id)
                link_already_exists = True
            except CampaignXListedByOrganization.DoesNotExist:
                link_already_exists = False
            except Exception as e:
                do_not_create = True
                messages.add_message(request, messages.ERROR, 'Link already exists.')
                status += "ADD_LISTED_CAMPAIGN_ALREADY_EXISTS: " + str(e) + " "

            if not do_not_create and not link_already_exists:
                # Now create new link
                try:
                    # Create the Campaign
                    CampaignXListedByOrganization.objects.create(
                        campaignx_we_vote_id=campaignx_listed_by_organization_campaignx_we_vote_id,
                        site_owner_organization_we_vote_id=organization_we_vote_id,
                        visible_to_public=campaignx_listed_by_organization_visible_to_public)

                    messages.add_message(request, messages.INFO, 'New CampaignXListedByOrganization created.')
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         'Could not create CampaignXListedByOrganization.'
                                         ' {error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    # ##################################
    # Deleting or Adding a new CampaignXListedByOrganization
    campaignx_manager = CampaignXManager()
    campaignx_listed_by_organization_list = campaignx_manager.retrieve_campaignx_listed_by_organization_list(
        site_owner_organization_we_vote_id=organization_we_vote_id,
        ignore_visible_to_public=True,
        read_only=False
    )
    for campaignx_listed_by_organization in campaignx_listed_by_organization_list:
        if positive_value_exists(campaignx_listed_by_organization.campaignx_we_vote_id):
            variable_name = "delete_campaignx_listed_by_organization_" + str(campaignx_listed_by_organization.id)
            delete_campaignx_listed_by_organization = positive_value_exists(request.POST.get(variable_name, False))
            if positive_value_exists(delete_campaignx_listed_by_organization):
                campaignx_listed_by_organization.delete()
                messages.add_message(request, messages.INFO, 'Deleted CampaignXListedByOrganization.')
            else:
                exists_variable_name = "campaignx_listed_by_organization_visible_to_public_" + \
                                str(campaignx_listed_by_organization.id) + "_exists"
                campaignx_listed_by_organization_visible_to_public_exists = request.POST.get(exists_variable_name, None)
                variable_name = "campaignx_listed_by_organization_visible_to_public_" + \
                                str(campaignx_listed_by_organization.id)
                campaignx_listed_by_organization_visible_to_public = \
                    positive_value_exists(request.POST.get(variable_name, False))
                if campaignx_listed_by_organization_visible_to_public_exists is not None:
                    campaignx_listed_by_organization.visible_to_public = \
                        campaignx_listed_by_organization_visible_to_public
                    campaignx_listed_by_organization.save()

    return HttpResponseRedirect(reverse('organization:organization_edit_listed_campaigns', args=(organization_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def organization_position_list_view(request, organization_id=0, organization_we_vote_id="", incorrect_integer=0):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = \
        {'partner_organization', 'political_data_manager', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    organization_search_for_merge = request.GET.get('organization_search_for_merge', "")
    # google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    candidate_id = request.GET.get('candidate_id', 0)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')

    # POST
    show_all_elections = positive_value_exists(request.POST.get('show_all_elections', False))

    # Bulk delete
    select_for_changing_position_ids = request.POST.getlist('select_for_marking_checks[]')
    which_marking = request.POST.get("which_marking", None)  # What to do with check marks

    # Make sure 'which_marking' is one of the allowed Filter fields
    if which_marking and which_marking not in ["delete_position", None]:
        messages.add_message(request, messages.ERROR,
                             'The action you chose from the dropdown is not recognized: {which_marking}'
                             ''.format(which_marking=which_marking))
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    error_count = 0
    items_processed_successfully = 0
    if which_marking and select_for_changing_position_ids:
        # Get these values from hidden POST fields
        # google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
        # show_all_elections = positive_value_exists(request.POST.get('show_all_elections', False))
        state_code = request.POST.get('state_code', '')  # Already retrieved with GET, now retrieving with POST

        position_manager = PositionManager()

        for position_we_vote_id in select_for_changing_position_ids:
            results = position_manager.retrieve_position_from_we_vote_id(position_we_vote_id)
            if results['position_found']:
                position = results['position']
                try:
                    if which_marking == "delete_position":
                        position.delete()
                        items_processed_successfully += 1
                    else:
                        status += 'ACTION_NOT_SPECIFIED '
                except Exception as e:
                    status += 'POSITION_ERROR: ' + str(e) + " "
                    error_count += 1
            else:
                status += 'POSITION_NOT_FOUND '

        messages.add_message(request, messages.INFO,
                             'Position List Actions successful: {items_processed_successfully}, '
                             'errors: {error_count}'
                             ''.format(error_count=error_count,
                                       items_processed_successfully=items_processed_successfully))

    # We pass candidate_we_vote_id to this page to pre-populate the form
    candidate_manager = CandidateManager()
    if positive_value_exists(candidate_we_vote_id):
        candidate_id = 0
        results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)
        if results['candidate_found']:
            candidate = results['candidate']
            candidate_id = candidate.id
    elif positive_value_exists(candidate_id):
        pass

    organization_on_stage = Organization()
    organization_on_stage_found = False
    organization_issues_list = []
    organization_blocked_issues_list = []
    organization_twitter_handle = ""
    try:
        if positive_value_exists(organization_id):
            organization_query = Organization.objects.filter(id=organization_id)
        else:
            organization_query = Organization.objects.filter(we_vote_id__iexact=organization_we_vote_id)
        if organization_query.count():
            organization_on_stage = organization_query[0]
            organization_on_stage_found = True
            organization_we_vote_id = organization_on_stage.we_vote_id
            organization_id = organization_on_stage.id
            organization_twitter_handle = organization_on_stage.organization_twitter_handle
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        organization_on_stage_found = False

    twitter_link_to_organization = None
    twitter_handle_mismatch = False
    if organization_on_stage_found:
        # TwitterLinkToOrganization
        twitter_user_manager = TwitterUserManager()
        results = twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization_we_vote_id)
        if results['twitter_link_to_organization_found']:
            twitter_link_to_organization = results['twitter_link_to_organization']
            twitter_link_to_organization_handle = \
                twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()
            if twitter_link_to_organization_handle and organization_twitter_handle:
                if twitter_link_to_organization_handle.lower() != organization_twitter_handle.lower():
                    twitter_handle_mismatch = True

    if not organization_on_stage_found:
        messages.add_message(request, messages.ERROR,
                             'Could not find organization when trying to retrieve positions.')
        return HttpResponseRedirect(reverse('organization:organization_list', args=()))

    friends_only_position_count = 0
    public_position_count = 0
    today = datetime.now().date()
    today_date_as_integer = convert_date_to_date_as_integer(today)

    is_analytics_admin = False
    authority_required = {'admin', 'analytics_admin'}
    if voter_has_authority(request, authority_required):
        is_analytics_admin = True

    try:
        public_position_query = PositionEntered.objects.all()
        # As of Aug 2018 we are no longer using PERCENT_RATING
        public_position_query = public_position_query.exclude(stance__iexact='PERCENT_RATING')
        public_position_query = public_position_query.filter(organization_id=organization_id)
        if positive_value_exists(show_all_elections):
            # Don't limit to positions for upcoming elections
            pass
        else:
            public_position_query = public_position_query \
                .filter(Q(position_ultimate_election_not_linked=True) |
                        Q(position_ultimate_election_date__gte=today_date_as_integer))
        public_position_query = public_position_query.order_by('-position_year')
        public_position_count = public_position_query.count()
        public_position_list = public_position_query[:50]
        public_position_list = list(public_position_list)

        if is_analytics_admin:
            friends_only_position_query = PositionForFriends.objects.all()
            # As of Aug 2018 we are no longer using PERCENT_RATING
            friends_only_position_query = friends_only_position_query.exclude(stance__iexact='PERCENT_RATING')
            friends_only_position_query = friends_only_position_query.filter(organization_id=organization_id)
            if positive_value_exists(show_all_elections):
                # Don't limit to positions for upcoming elections
                pass
            else:
                friends_only_position_query = friends_only_position_query \
                    .filter(Q(position_ultimate_election_not_linked=True) |
                            Q(position_ultimate_election_date__gte=today_date_as_integer))
            friends_only_position_query = friends_only_position_query.order_by('-id')
            friends_only_position_count = friends_only_position_query.count()
            friends_only_position_list = friends_only_position_query[:50]
            friends_only_position_list = list(friends_only_position_list)
        else:
            friends_only_position_list = []
            friends_only_position_count = 0

        organization_position_list = public_position_list + friends_only_position_list
        if len(public_position_list) or len(friends_only_position_list):
            organization_position_list_found = True

        link_issue_list_manager = OrganizationLinkToIssueList()
        organization_link_issue_list = link_issue_list_manager. \
            retrieve_issue_list_by_organization_we_vote_id(organization_we_vote_id)
        issue_manager = IssueManager()
        for link_issue in organization_link_issue_list:
            issue_object = issue_manager.fetch_issue_from_we_vote_id(link_issue.issue_we_vote_id)
            organization_issues_list.append(issue_object)

        organization_link_block_issue_list = link_issue_list_manager.\
            retrieve_issue_blocked_list_by_organization_we_vote_id(organization_we_vote_id)
        for blocked_issue in organization_link_block_issue_list:
            issue_object = issue_manager.fetch_issue_from_we_vote_id(blocked_issue.issue_we_vote_id)
            organization_blocked_issues_list.append(issue_object)

    except Exception as e:
        status += "COULD_NOT_RETRIEVE_POSITION_LIST: " + str(e) + ' '
        organization_position_list = []

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization_we_vote_id)
    if voter_results['voter_found']:
        organization_voter = voter_results['voter']
    else:
        organization_voter = None

    offices_dict = {}
    candidates_dict = {}
    measures_dict = {}
    organizations_dict = {}
    voters_by_linked_org_dict = {}
    voters_dict = {}
    position_manager = PositionManager()
    for one_position in organization_position_list:
        results = position_manager.refresh_cached_position_info(
            one_position, offices_dict=offices_dict, candidates_dict=candidates_dict, measures_dict=measures_dict,
            organizations_dict=organizations_dict, voters_by_linked_org_dict=voters_by_linked_org_dict,
            voters_dict=voters_dict)
        offices_dict = results['offices_dict']
        candidates_dict = results['candidates_dict']
        measures_dict = results['measures_dict']
        organizations_dict = results['organizations_dict']
        voters_by_linked_org_dict = results['voters_by_linked_org_dict']
        voters_dict = results['voters_dict']

    organization_search_results_list = []
    if positive_value_exists(organization_search_for_merge) and positive_value_exists(organization_we_vote_id):
        organization_query = Organization.objects.all()
        organization_query = organization_query.exclude(we_vote_id__iexact=organization_we_vote_id)

        search_words = organization_search_for_merge.split()
        for one_word in search_words:
            filters = []  # Reset for each search word
            new_filter = Q(organization_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_description__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_twitter_handle__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_instagram_handle__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                organization_query = organization_query.filter(final_filters)

        organization_search_results_list = list(organization_query)

    organization_type_display_text = ORGANIZATION_TYPE_MAP.get(organization_on_stage.organization_type,
                                                               ORGANIZATION_TYPE_MAP[UNKNOWN])

    campaignx_manager = CampaignXManager()
    campaignx_listed_by_organization_list = campaignx_manager.retrieve_campaignx_listed_by_organization_list(
        site_owner_organization_we_vote_id=organization_we_vote_id,
        ignore_visible_to_public=True,
        read_only=True
    )
    campaignx_listed_by_organization_list_modified = []
    # campaignx_listed_by_organization_list = campaignx_listed_by_organization_list[:3]
    for campaignx_listed_by_organization in campaignx_listed_by_organization_list:
        if positive_value_exists(campaignx_listed_by_organization.campaignx_we_vote_id):
            results = campaignx_manager.retrieve_campaignx(
                campaignx_we_vote_id=campaignx_listed_by_organization.campaignx_we_vote_id)
            if results['campaignx_found']:
                campaignx_listed_by_organization.campaign_title = results['campaignx'].campaign_title
        if positive_value_exists(campaignx_listed_by_organization.listing_requested_by_voter_we_vote_id):
            results = voter_manager.retrieve_voter_by_we_vote_id(
                campaignx_listed_by_organization.listing_requested_by_voter_we_vote_id,
                read_only=True)
            if results['voter_found']:
                campaignx_listed_by_organization.listing_requested_by_voter_name = results['voter'].get_full_name()
        campaignx_listed_by_organization_list_modified.append(campaignx_listed_by_organization)

    campaignx_owner_list_modified = []
    campaignx_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
        organization_we_vote_id=organization_we_vote_id,
        viewer_is_owner=True
    )

    organization_manager = OrganizationManager()
    organization_team_member_list = organization_manager.retrieve_team_member_list(
        organization_we_vote_id=organization_we_vote_id,
        read_only=True
    )

    for campaignx_owner in campaignx_owner_list:
        if positive_value_exists(campaignx_owner.campaignx_we_vote_id):
            results = campaignx_manager.retrieve_campaignx(
                campaignx_we_vote_id=campaignx_owner.campaignx_we_vote_id)
            if results['campaignx_found']:
                campaignx_owner.campaign_title = results['campaignx'].campaign_title
        campaignx_owner_list_modified.append(campaignx_owner)

    voter_device_id = get_voter_api_device_id(request)
    voter = fetch_voter_from_voter_device_link(voter_device_id)
    if hasattr(voter, 'is_admin') and voter.is_admin:
        queryset = OrganizationChangeLog.objects.using('readonly').all()
        queryset = queryset.filter(organization_we_vote_id__iexact=organization_we_vote_id)
        queryset = queryset.order_by('-log_datetime')
        change_log_list = list(queryset)
    else:
        change_log_list = []

    template_values = {
        'campaignx_listed_by_organization_list':    campaignx_listed_by_organization_list_modified,
        'campaignx_owner_list':             campaignx_owner_list_modified,
        'candidate_id':                     candidate_id,
        'candidate_we_vote_id':             candidate_we_vote_id,
        'change_log_list':                  change_log_list,
        'friends_only_position_count':      friends_only_position_count,
        'messages_on_stage':                messages_on_stage,
        'organization':                     organization_on_stage,
        'organization_issues_list':         organization_issues_list,
        'organization_blocked_issues_list': organization_blocked_issues_list,
        'organization_position_list':       organization_position_list,
        'organization_num_positions':       friends_only_position_count + public_position_count,
        'organization_search_for_merge':    organization_search_for_merge,
        'organization_search_results_list': organization_search_results_list,
        'organization_team_member_list':    organization_team_member_list,
        'organization_type_display_text':   organization_type_display_text,
        'organization_voter':               organization_voter,
        'public_position_count':            public_position_count,
        'show_all_elections':               show_all_elections,
        'twitter_handle_mismatch':          twitter_handle_mismatch,
        'twitter_link_to_organization':     twitter_link_to_organization,
        'voter':                            voter,
    }
    return render(request, 'organization/organization_position_list.html', template_values)


@login_required
def organization_position_new_view(request, organization_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    authority_results = retrieve_voter_authority(request)
    if not voter_has_authority(request, authority_required, authority_results):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    candidate_id = request.GET.get('candidate_id', 0)
    candidate_search = request.GET.get('candidate_search', False)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', False)
    measure_search = request.GET.get('measure_search', False)
    measure_we_vote_id = request.GET.get('measure_we_vote_id', False)
    state_code = request.GET.get('state_code', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))

    # Take in some incoming values
    candidate_and_measure_not_found = request.GET.get('candidate_and_measure_not_found', False)
    stance = request.GET.get('stance', SUPPORT)  # Set a default if stance comes in empty
    statement_text = request.GET.get('statement_text', '')  # Set a default if stance comes in empty
    more_info_url = request.GET.get('more_info_url', '')

    # We pass candidate_we_vote_id to this page to pre-populate the form
    candidate_manager = CandidateManager()
    if positive_value_exists(candidate_we_vote_id):
        candidate_id = 0
        results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)
        if results['candidate_found']:
            candidate = results['candidate']
            candidate_id = candidate.id
    elif positive_value_exists(candidate_id):
        pass

    # We pass candidate_we_vote_id to this page to pre-populate the form
    contest_measure_id = 0
    if positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)
        if results['contest_measure_found']:
            contest_measure = results['contest_measure']
            contest_measure_id = contest_measure.id

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    all_is_well = True
    organization_on_stage_found = False
    organization_on_stage = Organization()
    try:
        organization_on_stage = Organization.objects.get(id=organization_id)
        organization_on_stage_found = True
    except Organization.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Organization.DoesNotExist:
        # This is fine, create new
        pass

    if not organization_on_stage_found:
        messages.add_message(request, messages.INFO,
                             'Could not find organization when trying to create a new position.')
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    if positive_value_exists(google_civic_election_id):
        google_civic_election_id_list = [google_civic_election_id]
    elif not show_all_elections:
        google_civic_election_id_list = retrieve_upcoming_election_id_list(limit_to_this_state_code=state_code)
    else:
        google_civic_election_id_list = []

    # Prepare a dropdown of candidates competing in this election
    candidate_list = CandidateListManager()
    candidates_for_this_election_list = []
    results = candidate_list.retrieve_all_candidates_for_upcoming_election(
        google_civic_election_id_list=google_civic_election_id_list,
        state_code=state_code,
        search_string=candidate_search,
        return_list_of_objects=True,
        read_only=True)
    if results['candidate_list_found']:
        candidates_for_this_election_list = results['candidate_list_objects']

    # Prepare a drop down of measures in this election
    contest_measure_list = ContestMeasureListManager()
    contest_measures_for_this_election_list = []
    results = contest_measure_list.retrieve_all_measures_for_upcoming_election(
        google_civic_election_id_list=google_civic_election_id_list,
        state_code=state_code,
        search_string=measure_search,
        return_list_of_objects=True)
    if results['measure_list_found']:
        contest_measures_for_this_election_list = results['measure_list_objects']

    try:
        organization_position_query = PositionEntered.objects.order_by('stance')
        # As of Aug 2018 we are no longer using PERCENT_RATING
        organization_position_query = organization_position_query.exclude(stance__iexact='PERCENT_RATING')
        organization_position_query = organization_position_query.filter(organization_id=organization_id)
        if positive_value_exists(google_civic_election_id):
            organization_position_query = organization_position_query.filter(
                google_civic_election_id=google_civic_election_id)
        organization_position_list = organization_position_query.order_by(
            'google_civic_election_id', '-vote_smart_time_span')
        if len(organization_position_list):
            organization_position_list_found = True
    except Exception as e:
        organization_position_list = []

    if all_is_well:
        election_manager = ElectionManager()
        if positive_value_exists(show_all_elections):
            results = election_manager.retrieve_elections()
            election_list = results['election_list']
        else:
            results = election_manager.retrieve_upcoming_elections()
            election_list = results['election_list']
            # Make sure we always include the current election in the election_list, even if it is older
            if positive_value_exists(google_civic_election_id):
                this_election_found = False
                for one_election in election_list:
                    if convert_to_int(one_election.google_civic_election_id) ==\
                            convert_to_int(google_civic_election_id):
                        this_election_found = True
                        break
                if not this_election_found:
                    results = election_manager.retrieve_election(google_civic_election_id)
                    if results['election_found']:
                        one_election = results['election']
                        election_list.append(one_election)

        template_values = {
            'candidates_for_this_election_list':            candidates_for_this_election_list,
            'candidate_id':                                 candidate_id,
            'candidate_search':                             candidate_search
            if positive_value_exists(candidate_search) else '',
            'contest_measures_for_this_election_list':      contest_measures_for_this_election_list,
            'contest_measure_id':                           contest_measure_id,
            'measure_search':                               measure_search
            if positive_value_exists(measure_search) else '',
            'messages_on_stage':                            messages_on_stage,
            'organization':                                 organization_on_stage,
            'organization_position_candidate_id':           0,
            'possible_stances_list':                        ORGANIZATION_STANCE_CHOICES,
            'show_all_elections':                           show_all_elections,
            'stance_selected':                              stance,
            'election_list':                                election_list,
            'google_civic_election_id':                     google_civic_election_id,
            'state_code':                                   state_code,
            'organization_position_list':                   organization_position_list,
            'organization_num_positions':                   len(organization_position_list),
            'voter_authority':                              authority_results,
            # Incoming values from error state
            'candidate_and_measure_not_found':              candidate_and_measure_not_found,
            'stance':                                       stance,
            'statement_text':                               statement_text,
            'more_info_url':                                more_info_url,
        }
    return render(request, 'organization/organization_position_edit.html', template_values)


@login_required
def organization_delete_existing_position_process_form_view(request, organization_id, position_we_vote_id):
    """

    :param request:
    :param organization_id:
    :param position_we_vote_id:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_id = convert_to_int(organization_id)

    # Get the existing position
    organization_position_on_stage_found = False
    if positive_value_exists(position_we_vote_id):
        organization_position_on_stage = PositionEntered()
        organization_position_on_stage_found = False
        position_manager = PositionManager()
        results = position_manager.retrieve_position_from_we_vote_id(position_we_vote_id)
        if results['position_found']:
            organization_position_on_stage_found = True
            organization_position_on_stage = results['position']

    if not organization_position_on_stage_found:
        messages.add_message(request, messages.INFO,
                             "Could not find this organization's position when trying to delete.")
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    try:
        organization_position_on_stage.delete()
    except Exception as e:
        handle_record_not_deleted_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR,
                             'Could not delete position.')
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    messages.add_message(request, messages.INFO,
                         'Position deleted.')
    return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))


@login_required
def organization_politician_match_view(request):
    """
    Try to match the current organization to an existing politician entry. If a politician entry isn't found,
    create an entry.
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_id = request.GET.get('organization_id', 0)
    organization_id = convert_to_int(organization_id)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    # google_civic_election_id is included for interface usability reasons and isn't used in the processing
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    we_vote_organization = None

    organization_manager = OrganizationManager()
    if positive_value_exists(organization_we_vote_id):
        results = organization_manager.retrieve_organization(we_vote_id=organization_we_vote_id)
        if not positive_value_exists(results['organization_found']):
            messages.add_message(request, messages.ERROR,
                                 "Representative '{organization_we_vote_id}' not found."
                                 "".format(organization_we_vote_id=organization_we_vote_id))
            return HttpResponseRedirect(reverse('organization:organization_edit_we_vote_id',
                                                args=(organization_we_vote_id,)))
        we_vote_organization = results['organization']
    elif positive_value_exists(organization_id):
        results = organization_manager.retrieve_organization_from_id(organization_id)
        if not positive_value_exists(results['organization_found']):
            messages.add_message(request, messages.ERROR,
                                 "Representative '{organization_id}' not found."
                                 "".format(organization_id=organization_id))
            return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)))
        we_vote_organization = results['organization']
    else:
        messages.add_message(request, messages.ERROR, "Representative identifier was not passed in.")
        return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)))

    # Try to find existing politician for this organization. If none found, create politician.
    results = organization_politician_match(we_vote_organization)

    display_messages = True
    if results['status'] and display_messages:
        messages.add_message(request, messages.INFO, results['status'])
    return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def organization_position_edit_view(request, organization_id=0, organization_we_vote_id="", position_we_vote_id=""):
    """
    In edit, you can only change your stance and comments, not who or what the position is about
    :param request:
    :param organization_id:
    :param position_we_vote_id:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    organization_on_stage_found = False
    try:
        if positive_value_exists(organization_id):
            organization_on_stage = Organization.objects.get(id=organization_id)
        else:
            organization_on_stage = Organization.objects.get(we_vote_id=organization_we_vote_id)
        organization_on_stage_found = True
    except Organization.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Organization.DoesNotExist:
        # This is fine, create new
        pass

    if not organization_on_stage_found:
        messages.add_message(request, messages.INFO,
                             'Could not find organization when trying to edit a position.')
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    # Get the existing position
    organization_position_on_stage = PositionEntered()
    organization_position_on_stage_found = False
    position_manager = PositionManager()
    results = position_manager.retrieve_position_from_we_vote_id(position_we_vote_id)
    if results['position_found']:
        organization_position_on_stage_found = True
        organization_position_on_stage = results['position']

    if not organization_position_on_stage_found:
        messages.add_message(request, messages.INFO,
                             'Could not find organization position when trying to edit.')
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    # Note: We have access to the candidate through organization_position_on_stage.candidate

    election_manager = ElectionManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']
        # Make sure we always include the current election in the election_list, even if it is older
        if positive_value_exists(google_civic_election_id):
            this_election_found = False
            for one_election in election_list:
                if convert_to_int(one_election.google_civic_election_id) == convert_to_int(google_civic_election_id):
                    this_election_found = True
                    break
            if not this_election_found:
                results = election_manager.retrieve_election(google_civic_election_id)
                if results['election_found']:
                    one_election = results['election']
                    election_list.append(one_election)

    if organization_position_on_stage_found:
        template_values = {
            'is_in_edit_mode':                              True,
            'messages_on_stage':                            messages_on_stage,
            'organization':                                 organization_on_stage,
            'organization_position':                        organization_position_on_stage,
            'possible_stances_list':                        ORGANIZATION_STANCE_CHOICES,
            'show_all_elections':                           show_all_elections,
            'stance_selected':                              organization_position_on_stage.stance,
            'election_list':                                election_list,
            'google_civic_election_id':                     google_civic_election_id,
        }

    return render(request, 'organization/organization_position_edit.html', template_values)


@login_required
def organization_position_edit_process_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(request.POST.get('candidate_id', 0))
    candidate_search = request.POST.get('candidate_search', False)
    contest_measure_id = convert_to_int(request.POST.get('contest_measure_id', 0))
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    measure_search = request.POST.get('measure_search', False)
    more_info_url = request.POST.get('more_info_url', '')
    organization_id = convert_to_int(request.POST.get('organization_id', 0))
    position_we_vote_id = request.POST.get('position_we_vote_id', '')
    save_button = positive_value_exists(request.POST.get('save_button', False))
    show_all_elections = positive_value_exists(request.POST.get('show_all_elections', False))
    stance = request.POST.get('stance', SUPPORT)  # Set a default if stance comes in empty
    statement_text = request.POST.get('statement_text', '')  # Set a default if stance comes in empty

    go_back_to_add_new = False
    candidate_we_vote_id = ""
    google_civic_candidate_name = ""
    contest_measure_we_vote_id = ""
    google_civic_measure_title = ""
    candidate_on_stage_found = False
    contest_measure_on_stage_found = False
    organization_position_on_stage = PositionEntered()
    organization_on_stage = Organization()
    candidate_on_stage = CandidateCampaign()
    contest_measure_on_stage = ContestMeasure()
    state_code = ""
    position_manager = PositionManager()

    # Make sure this is a valid organization before we try to save a position
    organization_on_stage_found = False
    organization_we_vote_id = ""
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if organization_query.count():
            organization_on_stage = organization_query[0]
            organization_we_vote_id = organization_on_stage.we_vote_id
            organization_on_stage_found = True
    except Exception as e:
        # If we can't retrieve the organization, we cannot proceed
        handle_record_not_found_exception(e, logger=logger)

    if not organization_on_stage_found:
        messages.add_message(
            request, messages.ERROR,
            "Could not find the organization when trying to create or edit a new position.")
        return HttpResponseRedirect(reverse('organization:organization_list', args=()))

    # Now retrieve the CandidateCampaign or the ContestMeasure so we can save it with the Position
    # We need either candidate_id or contest_measure_id
    if candidate_id:
        try:
            candidate_on_stage = CandidateCampaign.objects.get(id=candidate_id)
            candidate_on_stage_found = True
            candidate_we_vote_id = candidate_on_stage.we_vote_id
            google_civic_candidate_name = candidate_on_stage.google_civic_candidate_name
            state_code = candidate_on_stage.state_code
        except CandidateCampaign.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except CandidateCampaign.DoesNotExist as e:
            handle_record_not_found_exception(e, logger=logger)

        if candidate_on_stage_found:
            pass
        else:
            messages.add_message(
                request, messages.ERROR,
                "Could not find Candidate's campaign when trying to create or edit a new position.")
            if positive_value_exists(position_we_vote_id):
                url_variables = "?google_civic_election_id=" + str(google_civic_election_id)
                url_variables += "&state_code=" + str(state_code)
                if positive_value_exists(show_all_elections):
                    url_variables += "&show_all_elections=1"
                url_variables += "&stance=" + str(stance)
                url_variables += "&statement_text=" + str(statement_text)
                url_variables += "&more_info_url=" + str(more_info_url)
                url_variables += "&candidate_and_measure_not_found=1"
                if positive_value_exists(candidate_search):
                    url_variables += "&candidate_search=" + str(candidate_search)
                if positive_value_exists(measure_search):
                    url_variables += "&measure_search=" + str(measure_search)

                return HttpResponseRedirect(
                    reverse('organization:organization_position_edit',
                            args=([organization_id], [position_we_vote_id])) + url_variables
                )
            else:
                url_variables = "?google_civic_election_id=" + str(google_civic_election_id)
                url_variables += "&state_code=" + str(state_code)
                if positive_value_exists(show_all_elections):
                    url_variables += "&show_all_elections=1"
                url_variables += "&stance=" + str(stance)
                url_variables += "&statement_text=" + str(statement_text)
                url_variables += "&more_info_url=" + str(more_info_url)
                url_variables += "&candidate_and_measure_not_found=1"
                if positive_value_exists(candidate_search):
                    url_variables += "&candidate_search=" + str(candidate_search)
                if positive_value_exists(measure_search):
                    url_variables += "&measure_search=" + str(measure_search)

                return HttpResponseRedirect(
                    reverse('organization:organization_position_new', args=([organization_id])) + url_variables
                )
        contest_measure_id = 0
    elif contest_measure_id:
        try:
            contest_measure_on_stage = ContestMeasure.objects.get(id=contest_measure_id)
            contest_measure_on_stage_found = True
            contest_measure_we_vote_id = contest_measure_on_stage.we_vote_id
            google_civic_measure_title = contest_measure_on_stage.google_civic_measure_title
            state_code = contest_measure_on_stage.state_code
        except CandidateCampaign.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except CandidateCampaign.DoesNotExist as e:
            handle_record_not_found_exception(e, logger=logger)

        if not contest_measure_on_stage_found:
            messages.add_message(
                request, messages.ERROR,
                "Could not find measure when trying to create or edit a new position.")
            if positive_value_exists(position_we_vote_id):
                url_variables = "?google_civic_election_id=" + str(google_civic_election_id)
                url_variables += "&state_code=" + str(state_code)
                if positive_value_exists(show_all_elections):
                    url_variables += "&show_all_elections=1"
                url_variables += "&stance=" + str(stance)
                url_variables += "&statement_text=" + str(statement_text)
                url_variables += "&more_info_url=" + str(more_info_url)
                url_variables += "&candidate_and_measure_not_found=1"
                if positive_value_exists(candidate_search):
                    url_variables += "&candidate_search=" + str(candidate_search)
                if positive_value_exists(measure_search):
                    url_variables += "&measure_search=" + str(measure_search)

                return HttpResponseRedirect(
                    reverse('organization:organization_position_edit',
                            args=([organization_id], [position_we_vote_id])) + url_variables
                )
            else:
                url_variables = "?google_civic_election_id=" + str(google_civic_election_id)
                url_variables += "&state_code=" + str(state_code)
                if positive_value_exists(show_all_elections):
                    url_variables += "&show_all_elections=1"
                url_variables += "&stance=" + str(stance)
                url_variables += "&statement_text=" + str(statement_text)
                url_variables += "&more_info_url=" + str(more_info_url)
                url_variables += "&candidate_and_measure_not_found=1"
                if positive_value_exists(candidate_search):
                    url_variables += "&candidate_search=" + str(candidate_search)
                if positive_value_exists(measure_search):
                    url_variables += "&measure_search=" + str(measure_search)

                return HttpResponseRedirect(
                    reverse('organization:organization_position_new', args=([organization_id])) + url_variables
                )
        candidate_id = 0
    else:
        if positive_value_exists(candidate_search):
            messages.add_message(
                request, messages.INFO,
                "Candidate drop-down limited to the search terms: '{candidate_search}'".format(
                    candidate_search=candidate_search
                ))
        if positive_value_exists(measure_search):
            messages.add_message(
                request, messages.INFO,
                "Measure drop-down limited to the search terms: '{measure_search}'".format(
                    measure_search=measure_search
                ))
        if not positive_value_exists(candidate_search) and not positive_value_exists(measure_search):
            messages.add_message(request, messages.INFO, "Please select a Candidate or a Measure.")
        url_variables = "?google_civic_election_id=" + str(google_civic_election_id)
        url_variables += "&state_code=" + str(state_code)
        if positive_value_exists(show_all_elections):
            url_variables += "&show_all_elections=1"
        url_variables += "&stance=" + str(stance)
        url_variables += "&statement_text=" + str(statement_text)
        url_variables += "&more_info_url=" + str(more_info_url)
        url_variables += "&candidate_and_measure_not_found=1"
        if positive_value_exists(candidate_search):
            url_variables += "&candidate_search=" + str(candidate_search)
        if positive_value_exists(measure_search):
            url_variables += "&measure_search=" + str(measure_search)

        return HttpResponseRedirect(
            reverse('organization:organization_position_new', args=([organization_id])) +
            url_variables
        )

    organization_position_on_stage_found = False

    # Retrieve position from position_we_vote_id if it exists already
    if positive_value_exists(position_we_vote_id):
        results = position_manager.retrieve_position_from_we_vote_id(position_we_vote_id)
        if results['position_found']:
            organization_position_on_stage_found = True
            organization_position_on_stage = results['position']

    organization_position_found_from_new_form = False
    if not organization_position_on_stage_found:  # Position not found from position_we_vote_id
        # If a position_we_vote_id hasn't been passed in, then we are trying to create a new position.
        # Check to make sure a position for this org, candidate and election doesn't already exist
        if candidate_id:
            results = position_manager.retrieve_organization_candidate_position(
                organization_id, candidate_id, google_civic_election_id)
        elif contest_measure_id:
            results = position_manager.retrieve_organization_contest_measure_position(
                organization_id, contest_measure_id, google_civic_election_id)
        else:
            messages.add_message(
                request, messages.ERROR,
                "Missing both candidate_id and contest_measure_id.")
            return HttpResponseRedirect(
                reverse('organization:organization_position_list', args=([organization_id]))
            )

        if results['MultipleObjectsReturned']:
            messages.add_message(
                request, messages.ERROR,
                "We found more than one existing positions for this candidate. Please delete all but one position.")
            return HttpResponseRedirect(
                reverse('organization:organization_position_list', args=([organization_id]))
            )
        elif results['position_found']:
            organization_position_on_stage_found = True
            organization_position_on_stage = results['position']
            organization_position_found_from_new_form = True

    # Now save existing, or create new
    if positive_value_exists(save_button):
        success = False
        try:
            if organization_position_on_stage_found:
                # Update the position
                organization_position_on_stage.stance = stance
                organization_position_on_stage.google_civic_election_id = google_civic_election_id
                if not organization_position_found_from_new_form or positive_value_exists(more_info_url):
                    # Only update this if we came from update form, or there is a value in the incoming variable
                    organization_position_on_stage.more_info_url = more_info_url
                if not organization_position_found_from_new_form or positive_value_exists(statement_text):
                    # Only update this if we came from update form, or there is a value in the incoming variable
                    organization_position_on_stage.statement_text = statement_text
                if not positive_value_exists(organization_position_on_stage.organization_we_vote_id):
                    organization_position_on_stage.organization_we_vote_id = organization_on_stage.we_vote_id
                organization_position_on_stage.candidate_campaign_id = candidate_id
                organization_position_on_stage.candidate_campaign_we_vote_id = candidate_we_vote_id
                organization_position_on_stage.google_civic_candidate_name = google_civic_candidate_name
                organization_position_on_stage.contest_measure_id = contest_measure_id
                organization_position_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                organization_position_on_stage.google_civic_measure_title = google_civic_measure_title
                organization_position_on_stage.state_code = state_code
                organization_position_on_stage.save()

                results = position_manager.refresh_cached_position_info(organization_position_on_stage)

                success = True

                if positive_value_exists(candidate_we_vote_id):
                    messages.add_message(
                        request, messages.INFO,
                        "Position on {candidate_name} updated.".format(
                            candidate_name=candidate_on_stage.display_candidate_name()))
                elif positive_value_exists(contest_measure_we_vote_id):
                    messages.add_message(
                        request, messages.INFO,
                        "Position on {measure_title} updated.".format(
                            measure_title=contest_measure_on_stage.measure_title))
            else:
                # Create new
                # Note that since we are processing a volunteer/admin entry tool, we can always save the PositionEntered
                # table, and don't need to worry about PositionForFriends
                organization_position_on_stage = PositionEntered(
                    organization_id=organization_id,
                    organization_we_vote_id=organization_we_vote_id,
                    candidate_campaign_id=candidate_id,
                    candidate_campaign_we_vote_id=candidate_we_vote_id,
                    google_civic_candidate_name=google_civic_candidate_name,
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=contest_measure_we_vote_id,
                    google_civic_measure_title=google_civic_measure_title,
                    google_civic_election_id=google_civic_election_id,
                    stance=stance,
                    statement_text=statement_text,
                    more_info_url=more_info_url,
                    state_code=state_code,
                )
                organization_position_on_stage.save()

                results = position_manager.refresh_cached_position_info(organization_position_on_stage)
                success = True

                if positive_value_exists(candidate_we_vote_id):
                    messages.add_message(
                        request, messages.INFO,
                        "New position on {candidate_name} saved.".format(
                            candidate_name=candidate_on_stage.display_candidate_name()))
                elif positive_value_exists(contest_measure_we_vote_id):
                    messages.add_message(
                        request, messages.INFO,
                        "New position on {measure_title} saved.".format(
                            measure_title=contest_measure_on_stage.measure_title))
                go_back_to_add_new = True
        except Exception as e:
            pass
        # If the position was saved, then update the voter_guide entry
        if success:
            voter_guide_manager = VoterGuideManager()
            voter_guide_we_vote_id = ''
            results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                voter_guide_we_vote_id, organization_on_stage.we_vote_id, google_civic_election_id, state_code)
            # if results['success']:
    else:
        go_back_to_add_new = True

    if go_back_to_add_new:
        url_variables = "?google_civic_election_id=" + str(google_civic_election_id)
        url_variables += "&state_code=" + str(state_code)
        if positive_value_exists(candidate_id):
            url_variables += "&candidate_id=" + str(candidate_id)
        if positive_value_exists(show_all_elections):
            url_variables += "&show_all_elections=1"
        url_variables += "&contest_measure_id=" + str(contest_measure_id)
        url_variables += "&stance=" + str(stance)
        url_variables += "&statement_text=" + str(statement_text)
        url_variables += "&more_info_url=" + str(more_info_url)

        return HttpResponseRedirect(
            reverse('organization:organization_position_new', args=(organization_on_stage.id,)) +
            url_variables)
    else:
        return HttpResponseRedirect(
            reverse('organization:organization_position_list', args=(organization_on_stage.id,)))


def render_organization_merge_form(
        request, organization_option1_for_template, organization_option2_for_template,
        organization_merge_conflict_values, remove_duplicate_process=True):
    organization_list_manager = OrganizationListManager()
    position_list_manager = PositionListManager()

    # Get positions counts for both organizations
    organization_option1_for_template.public_positions_count = \
        position_list_manager.fetch_public_positions_count_for_organization(
            organization_option1_for_template.id, organization_option1_for_template.we_vote_id)
    organization_option1_for_template.friends_positions_count = \
        position_list_manager.fetch_friends_only_positions_count_for_organization(
            organization_option1_for_template.id, organization_option1_for_template.we_vote_id)

    organization_option2_for_template.public_positions_count = \
        position_list_manager.fetch_public_positions_count_for_organization(
            organization_option2_for_template.id, organization_option2_for_template.we_vote_id)
    organization_option2_for_template.friends_positions_count = \
        position_list_manager.fetch_friends_only_positions_count_for_organization(
            organization_option2_for_template.id, organization_option2_for_template.we_vote_id)

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage': messages_on_stage,
        'organization_option1': organization_option1_for_template,
        'organization_option2': organization_option2_for_template,
        'conflict_values': organization_merge_conflict_values,
        'remove_duplicate_process': remove_duplicate_process,
    }
    return render(request, 'organization/organization_merge.html', template_values)


@login_required
def reserved_domain_edit_view(request):
    """
    In edit, you can only change your stance and comments, not who or what the position is about
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    reserved_domain_id = request.GET.get('reserved_domain_id', 0)
    reserved_domain_id = convert_to_int(reserved_domain_id)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    full_domain_string = ''
    subdomain_string = ''
    reserved_domain_found = False
    try:
        if positive_value_exists(reserved_domain_id):
            reserved_domain = OrganizationReservedDomain.objects.get(id=reserved_domain_id)
            full_domain_string = reserved_domain.full_domain_string
            subdomain_string = reserved_domain.subdomain_string
            reserved_domain_found = True
    except OrganizationReservedDomain.MultipleObjectsReturned as e:
        messages.add_message(request, messages.INFO,
                             'Could not find reserved domain when trying to edit.')
    except OrganizationReservedDomain.DoesNotExist:
        # This is fine, create new
        pass

    template_values = {
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'full_domain_string':       full_domain_string,
        'reserved_domain_id':       reserved_domain_id,
        'reserved_domain_found':    reserved_domain_found,
        'state_code':               state_code,
        'subdomain_string':         subdomain_string,
    }

    return render(request, 'organization/reserved_domain_edit.html', template_values)


@login_required
def reserved_domain_edit_process_view(request):
    """
    Process the new or edit reserved domain form
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    reserved_domain = None

    full_domain_string = request.POST.get('full_domain_string', '')
    reserved_domain_id = convert_to_int(request.POST.get('reserved_domain_id', 0))
    subdomain_string = request.POST.get('subdomain_string', '')

    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', False)

    if not positive_value_exists(full_domain_string) and not positive_value_exists(subdomain_string):
        messages.add_message(request, messages.INFO, 'Please enter either a full domain, or a sub domain.')
        messages_on_stage = get_messages(request)
        template_values = {
            'full_domain_string':       full_domain_string,
            'google_civic_election_id': google_civic_election_id,
            'messages_on_stage':        messages_on_stage,
            'reserved_domain_id':       reserved_domain_id,
            'state_code':               state_code,
            'subdomain_string':         subdomain_string,
        }

        return render(request, 'organization/reserved_domain_edit.html', template_values)

    # Check to see if this organization is already being used anywhere
    reserved_domain_found = False
    status = ""
    if positive_value_exists(reserved_domain_id):
        try:
            reserved_domain = OrganizationReservedDomain.objects.get(id=reserved_domain_id)
            reserved_domain_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find existing reserved domain.'
                                                          ' {error} [type: {error_type}]'
                                                          ''.format(error=e, error_type=type(e)))

    organization_domain_list = []
    reserved_domain_list = []
    if positive_value_exists(full_domain_string) or positive_value_exists(subdomain_string):
        # Double-check that we don't have a reserved entry already in the Organization table
        try:
            organization_list_query = Organization.objects.using('readonly').all()
            if positive_value_exists(full_domain_string):
                organization_list_query = organization_list_query.filter(
                    Q(chosen_domain_string__iexact=full_domain_string) |
                    Q(chosen_domain_string2__iexact=full_domain_string) |
                    Q(chosen_domain_string3__iexact=full_domain_string))

            else:
                organization_list_query = organization_list_query.\
                    filter(chosen_subdomain_string__iexact=subdomain_string)
            organization_domain_list = list(organization_list_query)
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find existing organization domain.'
                                                          ' {error} [type: {error_type}]'
                                                          ''.format(error=e, error_type=type(e)))

        # Double-check that we don't have a reserved entry already in the OrganizationReservedDomain table
        try:
            reserved_domain_list_query = OrganizationReservedDomain.objects.using('readonly').all()
            if positive_value_exists(reserved_domain_id):
                # Don't include this reserved_domain in the query
                reserved_domain_list_query = reserved_domain_list_query.exclude(id=reserved_domain_id)
            if positive_value_exists(full_domain_string):
                reserved_domain_list_query = reserved_domain_list_query.\
                    filter(full_domain_string__iexact=full_domain_string)
            else:
                reserved_domain_list_query = reserved_domain_list_query.\
                    filter(subdomain_string__iexact=subdomain_string)
            reserved_domain_list = list(reserved_domain_list_query)
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find existing reserved domain.'
                                                          ' {error} [type: {error_type}]'
                                                          ''.format(error=e, error_type=type(e)))

    if len(reserved_domain_list) or len(organization_domain_list):
        # Cannot save this entry
        messages.add_message(request, messages.INFO, 'Reserved domain already taken.')
        messages_on_stage = get_messages(request)
        template_values = {
            'full_domain_string':       full_domain_string,
            'google_civic_election_id': google_civic_election_id,
            'messages_on_stage':        messages_on_stage,
            'organization_domain_list': organization_domain_list,
            'reserved_domain_list':     reserved_domain_list,
            'reserved_domain_id':       reserved_domain_id,
            'state_code':               state_code,
            'subdomain_string':         subdomain_string,
        }

        return render(request, 'organization/reserved_domain_edit.html', template_values)

    if reserved_domain_found:
        # Update
        try:
            string_updated = ''
            if positive_value_exists(full_domain_string):
                reserved_domain.full_domain_string = full_domain_string.strip()
                string_updated = full_domain_string.strip()
            else:
                reserved_domain.full_domain_string = None
            if positive_value_exists(subdomain_string):
                reserved_domain.subdomain_string = subdomain_string.strip()
                string_updated = subdomain_string.strip()
            else:
                reserved_domain.subdomain_string = None
            reserved_domain.save()
            reserved_domain_id = reserved_domain.id

            messages.add_message(request, messages.INFO,
                                 'Reserved domain \'{string_updated}\' updated.'
                                 ''.format(string_updated=string_updated))
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not update reserved domain.'
                                                          ' {error} [type: {error_type}]'.format(error=e,
                                                                                                 error_type=type(e)))
    else:
        # Create new
        try:
            if positive_value_exists(full_domain_string):
                reserved_domain = OrganizationReservedDomain.objects.create(
                    full_domain_string=full_domain_string,
                )
                messages.add_message(request, messages.INFO, 'New reserved full domain saved.')
            elif positive_value_exists(subdomain_string):
                reserved_domain = OrganizationReservedDomain.objects.create(
                    subdomain_string=subdomain_string,
                )
                messages.add_message(request, messages.INFO, 'New reserved sub domain saved.')
            else:
                messages.add_message(request, messages.ERROR, 'Reserved full or sub domain not saved.')

        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not save new reserved domain.'
                                                          ' {error} [type: {error_type}]'.format(error=e,
                                                                                                 error_type=type(e)))
    return HttpResponseRedirect(reverse('organization:reserved_domain_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) + "&state_code=" +
                                str(state_code))


@login_required
def reserved_domain_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    domain_search = request.GET.get('domain_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    show_all = request.GET.get('show_all', False)
    show_full_domains = request.GET.get('show_full_domains', False)
    show_more = request.GET.get('show_more', False)
    show_subdomains = request.GET.get('show_subdomains', False)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)

    # ##########################################
    # Pull from OrganizationReservedDomain table
    reserved_domain_list_query = OrganizationReservedDomain.objects.using('readonly').all()
    if positive_value_exists(show_full_domains) and not positive_value_exists(show_subdomains):
        reserved_domain_list_query = reserved_domain_list_query.exclude(full_domain_string__isnull=True). \
            exclude(full_domain_string__exact='')
        reserved_domain_list_query = reserved_domain_list_query.order_by('full_domain_string')
    elif positive_value_exists(show_subdomains) and not positive_value_exists(show_full_domains):
        reserved_domain_list_query = reserved_domain_list_query.exclude(subdomain_string__isnull=True). \
            exclude(subdomain_string__exact='')
        reserved_domain_list_query = reserved_domain_list_query.order_by('subdomain_string')
    else:
        reserved_domain_list_query = reserved_domain_list_query.order_by('subdomain_string').\
            order_by('full_domain_string')

    if positive_value_exists(domain_search):
        search_words = domain_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(full_domain_string__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(subdomain_string__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                reserved_domain_list_query = reserved_domain_list_query.filter(final_filters)

    reserved_domain_count = reserved_domain_list_query.count()

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        reserved_domain_list = reserved_domain_list_query[:1000]
    elif positive_value_exists(show_all):
        reserved_domain_list = reserved_domain_list_query
    else:
        reserved_domain_list = reserved_domain_list_query[:200]

    # ##########################################
    # Pull from Organization table
    organization_domain_list_query = Organization.objects.using('readonly').all()
    # organization_domain_list_query = organization_domain_list_query. \
    #     exclude(chosen_domain_string__isnull=True). \
    #     exclude(chosen_domain_string__exact=''). \
    #     exclude(chosen_subdomain_string__isnull=True). \
    #     exclude(chosen_subdomain_string__exact='')
    if positive_value_exists(show_full_domains) and not positive_value_exists(show_subdomains):
        organization_domain_list_query = organization_domain_list_query.filter(
            Q(chosen_domain_string__isnull=False) |
            Q(chosen_domain_string2__isnull=False) |
            Q(chosen_domain_string3__isnull=False))
        organization_domain_list_query = organization_domain_list_query.order_by('chosen_domain_string')
    elif positive_value_exists(show_subdomains) and not positive_value_exists(show_full_domains):
        organization_domain_list_query = organization_domain_list_query.filter(chosen_subdomain_string__isnull=False)
        organization_domain_list_query = organization_domain_list_query.order_by('chosen_subdomain_string')
    else:
        organization_domain_list_query = organization_domain_list_query.filter(
            Q(chosen_domain_string__isnull=False) |
            Q(chosen_domain_string2__isnull=False) |
            Q(chosen_domain_string3__isnull=False) |
            Q(chosen_subdomain_string__isnull=False)
        )
        organization_domain_list_query = organization_domain_list_query.order_by('chosen_subdomain_string').\
            order_by('chosen_domain_string')

    if positive_value_exists(domain_search):
        search_words = domain_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(chosen_domain_string__icontains=one_word)
            filters.append(new_filter)

            filters = []
            new_filter = Q(chosen_domain_string2__icontains=one_word)
            filters.append(new_filter)

            filters = []
            new_filter = Q(chosen_domain_string3__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(chosen_subdomain_string__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                organization_domain_list_query = organization_domain_list_query.filter(final_filters)

    organization_domain_count = organization_domain_list_query.count()

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        organization_domain_list = organization_domain_list_query[:1000]
    elif positive_value_exists(show_all):
        organization_domain_list = organization_domain_list_query
    else:
        organization_domain_list = organization_domain_list_query[:200]

    if positive_value_exists(organization_domain_count) or positive_value_exists(reserved_domain_count):
        messages.add_message(request, messages.INFO,
                             '{reserved_domain_count:,} reserved domains found. '
                             '{organization_domain_count:,} organization domains found. '
                             ''.format(organization_domain_count=organization_domain_count,
                                       reserved_domain_count=reserved_domain_count))

    template_values = {
        'domain_search':            domain_search,
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'organization_domain_list': organization_domain_list,
        'reserved_domain_list':     reserved_domain_list,
        # 'show_all':                 show_all,
        # 'show_more':                show_more,
        'show_full_domains':        show_full_domains,
        'show_subdomains':          show_subdomains,
        # 'sort_by':                  sort_by,
        'state_code':               state_code,
    }
    return render(request, 'organization/reserved_domain_list.html', template_values)
