# organization/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import organizations_import_from_master_server, push_organization_data_to_other_table_caches
from .models import Organization, GROUP
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaign, CandidateCampaignListManager, CandidateCampaignManager
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_deleted_exception, handle_record_not_found_exception
from election.models import Election, ElectionManager
from issue.models import ALPHABETICAL_ASCENDING, IssueListManager, IssueManager, \
    OrganizationLinkToIssueList, OrganizationLinkToIssueManager
from measure.models import ContestMeasure, ContestMeasureList, ContestMeasureManager
import operator
from organization.models import OrganizationListManager, OrganizationManager, ORGANIZATION_TYPE_MAP, UNKNOWN
from position.models import PositionEntered, PositionManager, INFORMATION_ONLY, OPPOSE, \
    STILL_DECIDING, SUPPORT
from voter.models import retrieve_voter_authority, voter_has_authority, VoterManager
from voter_guide.models import VoterGuideManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, positive_value_exists, \
    STATE_CODE_MAP
from django.http import HttpResponse
import json


ORGANIZATION_STANCE_CHOICES = (
    (SUPPORT,           'We Support'),
    (OPPOSE,            'We Oppose'),
    (INFORMATION_ONLY,  'Information Only - No stance'),
    (STILL_DECIDING,    'We Are Still Deciding Our Stance'),
)

logger = wevote_functions.admin.get_logger(__name__)


def organization_retrieve_tweets_view():
    #For one organization, retrieve X Tweets, and capture all #Hashtags used.
    pass


# This page does not need to be protected.
def organizations_sync_out_view(request):  # organizationsSyncOut
    state_served_code = request.GET.get('state_served_code', '')

    try:
        organization_list = Organization.objects.using('readonly').all()
        if positive_value_exists(state_served_code):
            organization_list = organization_list.filter(state_served_code__iexact=state_served_code)
        organization_list_dict = organization_list.values(
            'we_vote_id', 'organization_name', 'organization_type',
            'organization_description', 'state_served_code',
            'organization_website', 'organization_email',
            'organization_image', 'organization_twitter_handle',
            'twitter_user_id', 'twitter_followers_count',
            'twitter_description', 'twitter_location', 'twitter_name',
            'twitter_profile_image_url_https',
            'twitter_profile_background_image_url_https',
            'twitter_profile_banner_url_https', 'organization_facebook',
            'vote_smart_id', 'organization_contact_name',
            'organization_address', 'organization_city',
            'organization_state', 'organization_zip',
            'organization_phone1', 'organization_phone2',
            'organization_fax', 'wikipedia_page_title',
            'wikipedia_page_id', 'wikipedia_photo_url',
            'wikipedia_thumbnail_url', 'wikipedia_thumbnail_width',
            'wikipedia_thumbnail_height', 'ballotpedia_page_title',
            'ballotpedia_photo_url')
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
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = organizations_import_from_master_server(request, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Organizations import completed. '
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')
    organization_search = request.GET.get('organization_search', '')
    organization_type_filter = request.GET.get('organization_type_filter', '')
    selected_issue_vote_id_list = request.GET.getlist('selected_issues', '')

    messages_on_stage = get_messages(request)
    organization_list_query = Organization.objects.all()
    organization_list_query = organization_list_query.order_by('organization_name')

    if positive_value_exists(state_code):
        organization_list_query = organization_list_query.filter(state_served_code__iexact=state_code)
    if positive_value_exists(organization_type_filter):
        organization_list_query = organization_list_query.filter(organization_type__iexact=organization_type_filter)

    # Retrieve all issues
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

            link_issue_list = OrganizationLinkToIssueList()
            organization_we_vote_id_list_result = link_issue_list.\
                retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list(selected_issue_vote_id_list)
            organization_we_vote_id_list = organization_we_vote_id_list_result['organization_we_vote_id_list']
            # we decided to not deal with case-insensitivity, in favor of using '__in'
            organization_list_query = organization_list_query.filter(we_vote_id__in=organization_we_vote_id_list)

    if positive_value_exists(organization_search):
        search_words = organization_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(organization_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_twitter_handle__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_website__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(twitter_description__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__icontains=one_word)
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

    # Limit to only showing 1000 on screen
    organization_list_query = organization_list_query[:1000]
    organization_list = organization_list_query

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    organization_types_map = ORGANIZATION_TYPE_MAP
    # Sort by organization_type value (instead of key)
    organization_types_list = sorted(organization_types_map.items(), key=operator.itemgetter(1))

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'candidate_we_vote_id':     candidate_we_vote_id,
        'google_civic_election_id': google_civic_election_id,
        'issue_list':               issue_list,
        'issues_selected':          issues_selected,
        'organization_type_filter': organization_type_filter,
        'organization_types':       organization_types_list,
        'organization_list':        organization_list,
        'organization_search':      organization_search,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'organization/organization_list.html', template_values)


@login_required
def organization_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
        issue_list_results = issue_list_manager.retrieve_issues(ALPHABETICAL_ASCENDING)
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

    organization_types_map = ORGANIZATION_TYPE_MAP
    # Sort by organization_type value (instead of key)
    organization_types_list = sorted(organization_types_map.items(), key=operator.itemgetter(1))

    if organization_on_stage_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'organization':             organization_on_stage,
            'organization_types':       organization_types_list,
            'upcoming_election_list':   upcoming_election_list,
            'google_civic_election_id': google_civic_election_id,
            'state_list':               sorted_state_list,
            'state_served_code':        state_served_code,
            'issue_list':               new_issue_list,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'upcoming_election_list':   upcoming_election_list,
            'google_civic_election_id': google_civic_election_id,
            'state_list':               sorted_state_list,
            'issue_list':               new_issue_list,
        }
    return render(request, 'organization/organization_edit.html', template_values)


@login_required
def organization_edit_process_view(request):
    """
    Process the new or edit organization forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_id = convert_to_int(request.POST.get('organization_id', 0))
    organization_name = request.POST.get('organization_name', '')
    organization_twitter_handle = request.POST.get('organization_twitter_handle', False)
    organization_facebook = request.POST.get('organization_facebook', False)
    organization_website = request.POST.get('organization_website', False)
    wikipedia_page_title = request.POST.get('wikipedia_page_title', False)
    wikipedia_photo_url = request.POST.get('wikipedia_photo_url', False)
    organization_endorsements_api_url = request.POST.get('organization_endorsements_api_url', False)
    state_served_code = request.POST.get('state_served_code', False)
    organization_link_issue_we_vote_ids = request.POST.getlist('selected_issues', False)
    organization_type = request.POST.get('organization_type', GROUP)

    # A positive value in google_civic_election_id or add_organization_button means we want to create a voter guide
    # for this org for this election
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')
    # add_organization_button = request.POST.get('add_organization_button', False)

    # Filter incoming data
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle)

    # Check to see if this organization is already being used anywhere
    organization_on_stage_found = False
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if organization_query.count():
            organization_on_stage = organization_query[0]
            organization_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if organization_on_stage_found:
            # Update
            if organization_name is not False:
                organization_on_stage.organization_name = organization_name
            if organization_twitter_handle is not False:
                organization_on_stage.organization_twitter_handle = organization_twitter_handle
            if organization_facebook is not False:
                organization_on_stage.organization_facebook = organization_facebook
            if organization_website is not False:
                organization_on_stage.organization_website = organization_website
            if wikipedia_page_title is not False:
                organization_on_stage.wikipedia_page_title = wikipedia_page_title
            if wikipedia_photo_url is not False:
                organization_on_stage.wikipedia_photo_url = wikipedia_photo_url
            if organization_endorsements_api_url is not False:
                organization_on_stage.organization_endorsements_api_url = organization_endorsements_api_url
            if state_served_code is not False:
                organization_on_stage.state_served_code = state_served_code
            if organization_type is not False:
                organization_on_stage.organization_type = organization_type
            organization_on_stage.save()
            organization_id = organization_on_stage.id
            organization_we_vote_id = organization_on_stage.we_vote_id

            push_organization_data_to_other_table_caches(organization_we_vote_id)

            messages.add_message(request, messages.INFO, 'Organization updated.')
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

                messages.add_message(request, messages.INFO, 'We found {count} existing organizations '
                                                             'that might match.'.format(count=organizations_count))
                messages_on_stage = get_messages(request)
                template_values = {
                    'messages_on_stage':            messages_on_stage,
                    'organizations_list':           organizations_list,
                    'organization_name':            organization_name,
                    'organization_twitter_handle':  organization_twitter_handle,
                    'organization_facebook':        organization_facebook,
                    'organization_website':         organization_website,
                    'wikipedia_page_title':         wikipedia_page_title,
                    'wikipedia_photo_url':          wikipedia_photo_url,
                }
                return render(request, 'organization/organization_edit.html', template_values)

            minimum_required_variables_exist = positive_value_exists(organization_name)
            if not minimum_required_variables_exist:
                messages.add_message(request, messages.INFO, 'Missing name, which is required.')
                messages_on_stage = get_messages(request)
                template_values = {
                    'messages_on_stage':            messages_on_stage,
                    'organization_name':            organization_name,
                    'organization_twitter_handle':  organization_twitter_handle,
                    'organization_facebook':        organization_facebook,
                    'organization_website':         organization_website,
                    'wikipedia_page_title':         wikipedia_page_title,
                    'wikipedia_photo_url':          wikipedia_photo_url,
                }
                return render(request, 'voter_guide/voter_guide_search.html', template_values)

            organization_on_stage = Organization(
                organization_name=organization_name,
            )
            if organization_twitter_handle is not False:
                organization_on_stage.organization_twitter_handle = organization_twitter_handle
            if organization_facebook is not False:
                organization_on_stage.organization_facebook = organization_facebook
            if organization_website is not False:
                organization_on_stage.organization_website = organization_website
            if wikipedia_page_title is not False:
                organization_on_stage.wikipedia_page_title = wikipedia_page_title
            if wikipedia_photo_url is not False:
                organization_on_stage.wikipedia_photo_url = wikipedia_photo_url
            if organization_endorsements_api_url is not False:
                organization_on_stage.organization_endorsements_api_url = organization_endorsements_api_url
            if state_served_code is not False:
                organization_on_stage.state_served_code = state_served_code
            if organization_type is not False:
                organization_on_stage.organization_type = organization_type
            organization_on_stage.save()
            organization_id = organization_on_stage.id
            organization_we_vote_id = organization_on_stage.we_vote_id
            messages.add_message(request, messages.INFO, 'New organization saved.')
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save organization.'
                                                      ' {error} [type: {error_type}]'.format(error=e,
                                                                                             error_type=type(e)))
        return HttpResponseRedirect(reverse('organization:organization_list', args=()))

    # Create voter_guide for this election?
    if positive_value_exists(google_civic_election_id) and positive_value_exists(organization_we_vote_id):
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            voter_guide_manager = VoterGuideManager()
            if positive_value_exists(state_served_code):
                state_code = state_served_code
            else:
                state_code = ""

            results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                organization_we_vote_id, google_civic_election_id, state_code)
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
    # this check necessary when, organization has issues linked previously, but all the
    # issues are unchecked
    if positive_value_exists(organization_follow_issues_we_vote_id_list_prior_to_update):
        # If a previously linked issue was NOT on the complete list of issues taken in above, unlink those issues
        for issue_we_vote_id in organization_follow_issues_we_vote_id_list_prior_to_update:
            link_issue_manager.unlink_organization_to_issue(organization_we_vote_id, issue_id, issue_we_vote_id)

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) + "&state_code=" +
                                str(state_code))


@login_required
def organization_position_list_view(request, organization_id=0, organization_we_vote_id="", incorrect_integer=0):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')

    organization_on_stage = Organization()
    organization_on_stage_found = False
    issue_names_list = []
    issue_blocked_names_list = []
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
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        organization_on_stage_found = False

    if not organization_on_stage_found:
        messages.add_message(request, messages.ERROR,
                             'Could not find organization when trying to retrieve positions.')
        return HttpResponseRedirect(reverse('organization:organization_list', args=()))
    else:
        organization_position_list_found = False
        try:
            organization_position_list = PositionEntered.objects.all()
            organization_position_list = organization_position_list.filter(organization_id=organization_id)
            if positive_value_exists(google_civic_election_id):
                organization_position_list = organization_position_list.filter(
                    google_civic_election_id=google_civic_election_id)
            organization_position_list = organization_position_list.order_by(
                '-google_civic_election_id', '-vote_smart_time_span')
            if len(organization_position_list):
                organization_position_list_found = True

            link_issue_list_manager = OrganizationLinkToIssueList()
            organization_link_issue_list = link_issue_list_manager. \
                retrieve_issue_list_by_organization_we_vote_id(organization_we_vote_id)
            issue_manager = IssueManager()
            for link_issue in organization_link_issue_list:
                issue_name = issue_manager.fetch_issue_name_from_we_vote_id(link_issue.issue_we_vote_id)
                issue_names_list.append(issue_name)

            organization_link_block_issue_list = link_issue_list_manager.\
                retrieve_issue_blocked_list_by_organization_we_vote_id(organization_we_vote_id)
            for blocked_issue in organization_link_block_issue_list:
                issue_name = issue_manager.fetch_issue_name_from_we_vote_id(blocked_issue.issue_we_vote_id)
                issue_blocked_names_list.append(issue_name)

        except Exception as e:
            organization_position_list = []

        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization_we_vote_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
        else:
            voter = None

        for one_position in organization_position_list:
            position_manager = PositionManager()
            one_position = position_manager.refresh_cached_position_info(one_position)

        election_list = Election.objects.order_by('-election_day_text')
        organization_type_display_text = ORGANIZATION_TYPE_MAP.get(organization_on_stage.organization_type,
                                                                   ORGANIZATION_TYPE_MAP[UNKNOWN])
        template_values = {
            'messages_on_stage':                messages_on_stage,
            'organization':                     organization_on_stage,
            'organization_position_list':       organization_position_list,
            'organization_num_positions':       len(organization_position_list),
            'organization_type_display_text':   organization_type_display_text,
            'election_list':                    election_list,
            'google_civic_election_id':         google_civic_election_id,
            'candidate_we_vote_id':             candidate_we_vote_id,
            'voter':                            voter,
            'issue_names_list':                 issue_names_list,
            'issue_blocked_names_list':         issue_blocked_names_list,
        }
    return render(request, 'organization/organization_position_list.html', template_values)


@login_required
def organization_position_new_view(request, organization_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    authority_results = retrieve_voter_authority(request)
    if not voter_has_authority(request, authority_required, authority_results):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', False)
    measure_we_vote_id = request.GET.get('measure_we_vote_id', False)
    state_code = request.GET.get('state_code', '')

    # Take in some incoming values
    candidate_and_measure_not_found = request.GET.get('candidate_and_measure_not_found', False)
    stance = request.GET.get('stance', SUPPORT)  # Set a default if stance comes in empty
    statement_text = request.GET.get('statement_text', '')  # Set a default if stance comes in empty
    more_info_url = request.GET.get('more_info_url', '')

    # We pass candidate_we_vote_id to this page to pre-populate the form
    candidate_campaign_id = 0
    if positive_value_exists(candidate_we_vote_id):
        candidate_campaign_manager = CandidateCampaignManager()
        results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
        if results['candidate_campaign_found']:
            candidate_campaign = results['candidate_campaign']
            candidate_campaign_id = candidate_campaign.id

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

    # Prepare a drop down of candidates competing in this election
    candidate_campaign_list = CandidateCampaignListManager()
    candidate_campaigns_for_this_election_list = []
    results = candidate_campaign_list.retrieve_all_candidates_for_upcoming_election(google_civic_election_id,
                                                                                    state_code, True)
    if results['candidate_list_found']:
        candidate_campaigns_for_this_election_list = results['candidate_list_objects']

    # Prepare a drop down of measures in this election
    contest_measure_list = ContestMeasureList()
    contest_measures_for_this_election_list = []
    results = contest_measure_list.retrieve_all_measures_for_upcoming_election(google_civic_election_id,
                                                                               state_code, True)
    if results['measure_list_found']:
        contest_measures_for_this_election_list = results['measure_list_objects']

    try:
        organization_position_list = PositionEntered.objects.order_by('stance')
        organization_position_list = organization_position_list.filter(organization_id=organization_id)
        if positive_value_exists(google_civic_election_id):
            organization_position_list = organization_position_list.filter(
                google_civic_election_id=google_civic_election_id)
        organization_position_list = organization_position_list.order_by(
            'google_civic_election_id', '-vote_smart_time_span')
        if len(organization_position_list):
            organization_position_list_found = True
    except Exception as e:
        organization_position_list = []

    if all_is_well:
        election_list = Election.objects.order_by('-election_day_text')
        template_values = {
            'candidate_campaigns_for_this_election_list':   candidate_campaigns_for_this_election_list,
            'candidate_campaign_id':                        candidate_campaign_id,
            'contest_measures_for_this_election_list':      contest_measures_for_this_election_list,
            'contest_measure_id':                           contest_measure_id,
            'messages_on_stage':                            messages_on_stage,
            'organization':                                 organization_on_stage,
            'organization_position_candidate_campaign_id':  0,
            'possible_stances_list':                        ORGANIZATION_STANCE_CHOICES,
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
    authority_required = {'admin'}  # admin, verified_volunteer
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
def organization_position_edit_view(request, organization_id, position_we_vote_id):
    """
    In edit, you can only change your stance and comments, not who or what the position is about
    :param request:
    :param organization_id:
    :param position_we_vote_id:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    organization_on_stage_found = False
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

    # Note: We have access to the candidate campaign through organization_position_on_stage.candidate_campaign

    election_list = Election.objects.all()

    if organization_position_on_stage_found:
        template_values = {
            'is_in_edit_mode':                              True,
            'messages_on_stage':                            messages_on_stage,
            'organization':                                 organization_on_stage,
            'organization_position':                        organization_position_on_stage,
            'possible_stances_list':                        ORGANIZATION_STANCE_CHOICES,
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    organization_id = convert_to_int(request.POST.get('organization_id', 0))
    position_we_vote_id = request.POST.get('position_we_vote_id', '')
    candidate_campaign_id = convert_to_int(request.POST.get('candidate_campaign_id', 0))
    contest_measure_id = convert_to_int(request.POST.get('contest_measure_id', 0))
    stance = request.POST.get('stance', SUPPORT)  # Set a default if stance comes in empty
    statement_text = request.POST.get('statement_text', '')  # Set a default if stance comes in empty
    more_info_url = request.POST.get('more_info_url', '')

    go_back_to_add_new = False
    candidate_campaign_we_vote_id = ""
    google_civic_candidate_name = ""
    contest_measure_we_vote_id = ""
    google_civic_measure_title = ""
    candidate_campaign_on_stage_found = False
    contest_measure_on_stage_found = False
    organization_position_on_stage = PositionEntered()
    organization_on_stage = Organization()
    candidate_campaign_on_stage = CandidateCampaign()
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
    # We need either candidate_campaign_id or contest_measure_id
    if candidate_campaign_id:
        try:
            candidate_campaign_on_stage = CandidateCampaign.objects.get(id=candidate_campaign_id)
            candidate_campaign_on_stage_found = True
            candidate_campaign_we_vote_id = candidate_campaign_on_stage.we_vote_id
            google_civic_candidate_name = candidate_campaign_on_stage.google_civic_candidate_name
            state_code = candidate_campaign_on_stage.state_code
        except CandidateCampaign.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except CandidateCampaign.DoesNotExist as e:
            handle_record_not_found_exception(e, logger=logger)

        if not candidate_campaign_on_stage_found:
            messages.add_message(
                request, messages.ERROR,
                "Could not find Candidate's campaign when trying to create or edit a new position.")
            if positive_value_exists(position_we_vote_id):
                return HttpResponseRedirect(
                    reverse('organization:organization_position_edit', args=([organization_id], [position_we_vote_id])) +
                    "?google_civic_election_id=" + str(google_civic_election_id) +
                    "&state_code=" + str(state_code) +
                    "&stance=" + stance +
                    "&statement_text=" + statement_text +
                    "&more_info_url=" + more_info_url +
                    "&candidate_and_measure_not_found=1"
                )
            else:
                return HttpResponseRedirect(
                    reverse('organization:organization_position_new', args=([organization_id])) +
                    "?google_civic_election_id=" + str(google_civic_election_id) +
                    "&state_code=" + str(state_code) +
                    "&stance=" + stance +
                    "&statement_text=" + statement_text +
                    "&more_info_url=" + more_info_url +
                    "&candidate_and_measure_not_found=1"
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
                return HttpResponseRedirect(
                    reverse('organization:organization_position_edit', args=([organization_id], [position_we_vote_id])) +
                    "?google_civic_election_id=" + str(google_civic_election_id) +
                    "&state_code=" + str(state_code) +
                    "&stance=" + stance +
                    "&statement_text=" + statement_text +
                    "&more_info_url=" + more_info_url +
                    "&candidate_and_measure_not_found=1"
                )
            else:
                return HttpResponseRedirect(
                    reverse('organization:organization_position_new', args=([organization_id])) +
                    "?google_civic_election_id=" + str(google_civic_election_id) +
                    "&state_code=" + str(state_code) +
                    "&stance=" + stance +
                    "&statement_text=" + statement_text +
                    "&more_info_url=" + more_info_url +
                    "&candidate_and_measure_not_found=1"
                )
        candidate_campaign_id = 0
    else:
        messages.add_message(
            request, messages.ERROR,
            "Unable to find either Candidate or Measure.")
        return HttpResponseRedirect(
            reverse('organization:organization_position_new', args=([organization_id])) +
            "?google_civic_election_id=" + str(google_civic_election_id) +
            "&state_code=" + str(state_code) +
            "&stance=" + stance +
            "&statement_text=" + statement_text +
            "&more_info_url=" + more_info_url +
            "&candidate_and_measure_not_found=1"
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
        if candidate_campaign_id:
            results = position_manager.retrieve_organization_candidate_campaign_position(
                organization_id, candidate_campaign_id, google_civic_election_id)
        elif contest_measure_id:
            results = position_manager.retrieve_organization_contest_measure_position(
                organization_id, contest_measure_id, google_civic_election_id)
        else:
            messages.add_message(
                request, messages.ERROR,
                "Missing both candidate_campaign_id and contest_measure_id.")
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
            organization_position_on_stage.candidate_campaign_id = candidate_campaign_id
            organization_position_on_stage.candidate_campaign_we_vote_id = candidate_campaign_we_vote_id
            organization_position_on_stage.google_civic_candidate_name = google_civic_candidate_name
            organization_position_on_stage.contest_measure_id = contest_measure_id
            organization_position_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
            organization_position_on_stage.google_civic_measure_title = google_civic_measure_title
            organization_position_on_stage.state_code = state_code
            organization_position_on_stage.save()

            organization_position_on_stage = position_manager.refresh_cached_position_info(
                organization_position_on_stage)

            success = True

            if positive_value_exists(candidate_campaign_we_vote_id):
                messages.add_message(
                    request, messages.INFO,
                    "Position on {candidate_name} updated.".format(
                        candidate_name=candidate_campaign_on_stage.display_candidate_name()))
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
                candidate_campaign_id=candidate_campaign_id,
                candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
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

            organization_position_on_stage = position_manager.refresh_cached_position_info(
                organization_position_on_stage)
            success = True

            if positive_value_exists(candidate_campaign_we_vote_id):
                messages.add_message(
                    request, messages.INFO,
                    "New position on {candidate_name} saved.".format(
                        candidate_name=candidate_campaign_on_stage.display_candidate_name()))
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
        results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
            organization_on_stage.we_vote_id, google_civic_election_id, state_code)
        # if results['success']:

    if go_back_to_add_new:
        return HttpResponseRedirect(
            reverse('organization:organization_position_new', args=(organization_on_stage.id,)) +
            "?google_civic_election_id=" + str(google_civic_election_id) + "&state_code=" + str(state_code))
    else:
        return HttpResponseRedirect(
            reverse('organization:organization_position_list', args=(organization_on_stage.id,)))
