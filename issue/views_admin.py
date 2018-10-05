# issue/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import *
from .models import ALPHABETICAL_ASCENDING, Issue, OrganizationLinkToIssue
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import ElectionManager
from exception.models import handle_record_found_more_than_one_exception
from image.controllers import cache_issue_image_master, cache_resized_image_locally, delete_cached_images_for_issue
from image.models import WeVoteImageManager
from organization.models import OrganizationManager, OrganizationListManager
from voter.models import voter_has_authority
from voter_guide.models import VoterGuideListManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, get_voter_device_id, STATE_CODE_MAP
from django.http import HttpResponse
import json

ORGANIZATION_LINK_TO_ISSUE_SYNC_URL = \
    get_environment_variable("ORGANIZATION_LINK_TO_ISSUE_SYNC_URL")  # organizationLinkToIssueSyncOut
ISSUES_SYNC_URL = get_environment_variable("ISSUES_SYNC_URL")  # issuesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
def issues_sync_out_view(request):  # issuesSyncOut
    issue_search = request.GET.get('issue_search', '')

    try:
        issue_list = Issue.objects.all()
        filters = []
        if positive_value_exists(issue_search):
            new_filter = Q(issue_name__icontains=issue_search)
            filters.append(new_filter)

            new_filter = Q(issue_description__icontains=issue_search)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__icontains=issue_search)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                issue_list = issue_list.filter(final_filters)

        issue_list_dict = issue_list.values('we_vote_id', 'hide_issue',
                                            'issue_name', 'issue_description', 'issue_image_url',
                                            'issue_followers_count', 'linked_organization_count',
                                            'we_vote_hosted_image_url_large', 'we_vote_hosted_image_url_medium',
                                            'we_vote_hosted_image_url_tiny')
        if issue_list_dict:
            issue_list_json = list(issue_list_dict)
            return HttpResponse(json.dumps(issue_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'ISSUES_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def issues_retrieve_view(request):  # issuesRetrieve
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    sort_formula = request.GET.get('sort_formula', ALPHABETICAL_ASCENDING)  # Alternate: MOST_LINKED_ORGANIZATIONS
    ballot_location_shortcut = request.GET.get('ballot_location_shortcut', False)
    ballot_returned_we_vote_id = request.GET.get('ballot_returned_we_vote_id', False)
    google_civic_election_id = request.GET.get('google_civic_election_id', False)
    voter_issues_only = request.GET.get('voter_issues_only', False)
    include_voter_follow_status = request.GET.get('include_voter_follow_status', False)
    http_response = issues_retrieve_for_api(voter_device_id, sort_formula, google_civic_election_id,
                                            voter_issues_only, include_voter_follow_status,
                                            ballot_location_shortcut, ballot_returned_we_vote_id)
    return http_response


def retrieve_issues_to_follow_view(request):  # retrieveIssuesToFollow
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    sort_formula = request.GET.get('sort_formula', ALPHABETICAL_ASCENDING)  # Alternate: MOST_LINKED_ORGANIZATIONS
    http_response = retrieve_issues_to_follow_for_api(voter_device_id, sort_formula)
    return http_response


@login_required
def issues_import_from_master_server_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in ISSUES_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = issues_import_from_master_server(request)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Issues import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['issues_saved'],
                                                               updated=results['issues_updated'],
                                                               not_processed=results['issues_not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required
def issue_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_manager', 'political_data_viewer',
                          'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    issue_search = request.GET.get('issue_search', '')
    show_hidden_issues = request.GET.get('show_hidden_issues', False)
    show_all_elections = request.GET.get('show_all_elections', False)

    issue_list_count = 0

    issue_we_vote_id_list = []
    organization_we_vote_id_in_this_election_list = []
    organization_retrieved_list = {}
    organization_link_to_issue_list = []
    organizations_attached_to_this_issue = {}
    if positive_value_exists(google_civic_election_id):
        # If we are just looking at one election, then we want to retrieve a list of the voter guides associated
        #  with this election. This way we can order the issues based on the number of organizations with positions
        #  in this election linked to issues.
        voter_guide_list_manager = VoterGuideListManager()
        organization_manager = OrganizationManager()
        results = voter_guide_list_manager.retrieve_voter_guides_for_election(google_civic_election_id)
        if results['voter_guide_list_found']:
            voter_guide_list = results['voter_guide_list']
            for one_voter_guide in voter_guide_list:
                organization_we_vote_id_in_this_election_list.append(one_voter_guide.organization_we_vote_id)
            # try:
            if positive_value_exists(len(organization_we_vote_id_in_this_election_list)):
                organization_link_to_issue_list_query = OrganizationLinkToIssue.objects.all()
                organization_link_to_issue_list_query = organization_link_to_issue_list_query.filter(
                    organization_we_vote_id__in=organization_we_vote_id_in_this_election_list)
                organization_link_to_issue_list = list(organization_link_to_issue_list_query)
            for one_organization_link_to_issue in organization_link_to_issue_list:
                if one_organization_link_to_issue.organization_we_vote_id not in organization_retrieved_list:
                    # If here, we need to retrieve the organization
                    organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                        one_organization_link_to_issue.organization_we_vote_id)
                    if organization_results['organization_found']:
                        organization_object = organization_results['organization']
                        organization_retrieved_list[one_organization_link_to_issue.organization_we_vote_id] = \
                            organization_object
                if one_organization_link_to_issue.issue_we_vote_id not in organizations_attached_to_this_issue:
                    organizations_attached_to_this_issue[one_organization_link_to_issue.issue_we_vote_id] = []
                organizations_attached_to_this_issue[one_organization_link_to_issue.issue_we_vote_id].\
                    append(
                    organization_retrieved_list[one_organization_link_to_issue.organization_we_vote_id])
                # if one_organization_link_to_issue.issue_we_vote_id not in issue_we_vote_id_list:
                #     issue_we_vote_id_list.append(one_organization_link_to_issue.issue_we_vote_id)

            # except Exception as e:
            #     pass

    try:
        issue_list_query = Issue.objects.all()

        if positive_value_exists(show_hidden_issues) or positive_value_exists(issue_search):
            # If trying to show hidden issues, no change to the query needed
            pass
        else:
            # By default, we only show the issues marked "hide_issue=False"
            issue_list_query = issue_list_query.filter(hide_issue=False)

        # if positive_value_exists(len(issue_we_vote_id_list)):
        #     issue_list_query = issue_list_query.filter(we_vote_id__in=issue_we_vote_id_list)

        if positive_value_exists(issue_search):
            search_words = issue_search.split()
            for one_word in search_words:
                filters = []
                new_filter = Q(issue_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(issue_description__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    issue_list_query = issue_list_query.filter(final_filters)

        issue_list_query = issue_list_query.order_by('issue_name')
        issue_list_count = issue_list_query.count()

        issue_list = list(issue_list_query)

        if issue_list_count:
            altered_issue_list = []
            organization_link_to_issue_list_manager = OrganizationLinkToIssueList()
            # Update the linked_organization_count
            for one_issue in issue_list:
                one_issue.linked_organization_count = \
                    organization_link_to_issue_list_manager.fetch_linked_organization_count(one_issue.we_vote_id)
                try:
                    one_issue.save()
                except Exception as e:
                    pass
                if one_issue.we_vote_id in organizations_attached_to_this_issue:
                    one_issue.linked_organization_list = organizations_attached_to_this_issue[one_issue.we_vote_id]
                    one_issue.linked_organization_list_count = len(one_issue.linked_organization_list)
                else:
                    one_issue.linked_organization_list = []
                    one_issue.linked_organization_list_count = 0
                altered_issue_list.append(one_issue)
        else:
            altered_issue_list = issue_list
    except Issue.DoesNotExist:
        # This is fine
        altered_issue_list = []
        pass

    # Order based on number of organizations per issue
    altered_issue_list.sort(key=lambda x: x.linked_organization_list_count, reverse=True)

    status_print_list = ""
    status_print_list += "issue_list_count: " + \
                         str(issue_list_count) + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    election_manager = ElectionManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    template_values = {
        'election_list':            election_list,
        'google_civic_election_id': google_civic_election_id,
        'issue_list':               altered_issue_list,
        'issue_search':             issue_search,
        'messages_on_stage':        messages_on_stage,
        'show_all_elections':       show_all_elections,
        'show_hidden_issues':       positive_value_exists(show_hidden_issues),
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'issue/issue_list.html', template_values)


@login_required
def issue_new_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    issue_name = request.GET.get('issue_name', "")
    issue_description = request.GET.get('issue_description', "")
    issue_image_url = request.GET.get('issue_image_url', "")
    hide_issue = request.GET.get('hide_issue', True)  # Default to true

    # Its helpful to see existing issues when entering a new issue
    issue_list = []
    try:
        issue_list = Issue.objects.all()
        issue_list = issue_list.order_by('issue_name')[:500]
    except Issue.DoesNotExist:
        # This is fine
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'google_civic_election_id': google_civic_election_id,
        'hide_issue':           hide_issue,
        'issue_list':           issue_list,
        'issue_name':           issue_name,
        'issue_description':    issue_description,
        'issue_image_url':      issue_image_url,
        'messages_on_stage':    messages_on_stage,
        'state_code': state_code,
    }
    return render(request, 'issue/issue_edit.html', template_values)


@login_required
def issue_edit_view(request, issue_we_vote_id):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    # These variables are here in case there was an error on the edit_process_view and the voter needs to try again
    hide_issue = request.GET.get('hide_issue', True)
    issue_name = request.GET.get('issue_name', '')
    issue_description = request.GET.get('issue_description', '')
    issue_image_url = request.GET.get('issue_image_url', '')
    issue_image_file = request.GET.get('issue_image_file', '')

    messages_on_stage = get_messages(request)
    issue_on_stage_found = False
    issue_on_stage = Issue()
    organization_list = []

    try:
        issue_on_stage = Issue.objects.get(we_vote_id__iexact=issue_we_vote_id)
        issue_on_stage_found = True
    except Issue.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Issue.DoesNotExist:
        # This is fine, create new below
        pass

    # Its helpful to see existing issues when entering a new issue
    issue_list = []
    try:
        issue_list = Issue.objects.all()
        issue_list = issue_list.order_by('issue_name')[:500]
    except Issue.DoesNotExist:
        # This is fine
        pass

    if issue_on_stage_found:
        issue_on_stage_list = []
        issue_on_stage_list.append(issue_we_vote_id)
        organization_link_to_issue_list_manager = OrganizationLinkToIssueList()
        organization_results = \
            organization_link_to_issue_list_manager.retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list(
                issue_on_stage_list)
        if organization_results['organization_we_vote_id_list_found']:
            organization_list_manager = OrganizationListManager()
            organization_we_vote_id_list = organization_results['organization_we_vote_id_list']
            organization_list_results = \
                organization_list_manager.retrieve_organizations_by_organization_we_vote_id_list(
                    organization_we_vote_id_list)
            if organization_list_results['organization_list_found']:
                organization_list = organization_list_results['organization_list']

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'hide_issue':               hide_issue,
        'issue_list':               issue_list,
        'issue':                    issue_on_stage,
        'issue_name':               issue_name,
        'issue_description':        issue_description,
        'issue_image_url':          issue_image_url,
        'issue_image_file':         issue_image_file,
        'google_civic_election_id': google_civic_election_id,
        'state_code':               state_code,
        'organization_list':        organization_list,
    }

    return render(request, 'issue/issue_edit.html', template_values)


@login_required
def issue_edit_process_view(request):
    """
    Process the new or edit issue forms
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    master_we_vote_hosted_image_url = None
    we_vote_hosted_image_url_large = None
    we_vote_hosted_image_url_medium = None
    we_vote_hosted_image_url_tiny = None

    hide_issue = request.POST.get('hide_issue', False)
    issue_we_vote_id = request.POST.get('issue_we_vote_id', False)
    issue_name = request.POST.get('issue_name', False)
    issue_description = request.POST.get('issue_description', False)
    issue_image_url = request.POST.get('issue_image_url', False)  # Maintain manual image entry for now
    try:
        if request.method == 'POST' and request.FILES['issue_image_file']:
            issue_image_file = request.FILES.get('issue_image_file')
            cache_issue_image_results = cache_issue_image_master(
                google_civic_election_id, issue_image_file, issue_we_vote_id=issue_we_vote_id,
                kind_of_image_issue=True, kind_of_image_original=True)
            we_vote_image_manager = WeVoteImageManager()
            if cache_issue_image_results['success']:
                cached_master_we_vote_image = cache_issue_image_results['we_vote_image']
                google_civic_election_id = cached_master_we_vote_image.google_civic_election_id
                we_vote_parent_image_id = cached_master_we_vote_image.id
                image_format = cached_master_we_vote_image.we_vote_image_file_location.split(".")[-1]
                master_we_vote_hosted_image_url = cached_master_we_vote_image.we_vote_image_url
                cache_large_resized_image_results = cache_resized_image_locally(
                    google_civic_election_id, master_we_vote_hosted_image_url, we_vote_parent_image_id,
                    issue_we_vote_id=issue_we_vote_id, image_format=image_format,
                    kind_of_image_issue=True, kind_of_image_large=True)
                if cache_large_resized_image_results['success']:
                    cached_resized_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                        issue_we_vote_id=issue_we_vote_id, issue_image_url_https=master_we_vote_hosted_image_url,
                        kind_of_image_large=True)
                    if cached_resized_image_results['success']:
                        we_vote_hosted_image_url_large = \
                            cached_resized_image_results['we_vote_image'].we_vote_image_url

                cache_medium_resized_image_results = cache_resized_image_locally(
                    google_civic_election_id, master_we_vote_hosted_image_url, we_vote_parent_image_id,
                    issue_we_vote_id=issue_we_vote_id, image_format=image_format,
                    kind_of_image_issue=True, kind_of_image_medium=True)
                if cache_medium_resized_image_results['success']:
                    cached_resized_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                        issue_we_vote_id=issue_we_vote_id, issue_image_url_https=master_we_vote_hosted_image_url,
                        kind_of_image_medium=True)
                    if cached_resized_image_results['success']:
                        we_vote_hosted_image_url_medium = \
                            cached_resized_image_results['we_vote_image'].we_vote_image_url

                cache_tiny_resized_image_results = cache_resized_image_locally(
                    google_civic_election_id, master_we_vote_hosted_image_url, we_vote_parent_image_id,
                    issue_we_vote_id=issue_we_vote_id, image_format=image_format,
                    kind_of_image_issue=True, kind_of_image_tiny=True)
                if cache_tiny_resized_image_results['success']:
                    cached_resized_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                        issue_we_vote_id=issue_we_vote_id, issue_image_url_https=master_we_vote_hosted_image_url,
                        kind_of_image_tiny=True)
                    if cached_resized_image_results['success']:
                        we_vote_hosted_image_url_tiny = \
                            cached_resized_image_results['we_vote_image'].we_vote_image_url

    except KeyError as e:
        pass

    # Check to see if this issue is already being used anywhere
    issue_on_stage_found = False
    issue_on_stage = Issue()
    if positive_value_exists(issue_we_vote_id):
        try:
            issue_on_stage = Issue.objects.get(we_vote_id__iexact=issue_we_vote_id)
            issue_on_stage_found = True
        except Issue.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except Issue.DoesNotExist:
            # This is fine, create new below
            pass

    if issue_on_stage_found:
        # Update
        if issue_name is not False:
            issue_on_stage.issue_name = issue_name
        if issue_description is not False:
            issue_on_stage.issue_description = issue_description
        if issue_image_url is not None:
            issue_on_stage.issue_image_url = issue_image_url
        if we_vote_hosted_image_url_large is not None:
            issue_on_stage.we_vote_hosted_image_url_large = we_vote_hosted_image_url_large
        if we_vote_hosted_image_url_medium is not None:
            issue_on_stage.we_vote_hosted_image_url_medium = we_vote_hosted_image_url_medium
        if we_vote_hosted_image_url_tiny is not None:
            issue_on_stage.we_vote_hosted_image_url_tiny = we_vote_hosted_image_url_tiny
        issue_on_stage.hide_issue = hide_issue

        issue_on_stage.save()
        issue_we_vote_id = issue_on_stage.we_vote_id

        messages.add_message(request, messages.INFO, 'Issue updated.')
    else:
        # Create new
        required_issue_variables = True if positive_value_exists(issue_name) else False
        if required_issue_variables:
            issue_on_stage = Issue(
                issue_name=issue_name,
            )
            if issue_description is not False:
                issue_on_stage.issue_description = issue_description
            if issue_image_url is not None:
                issue_on_stage.issue_image_url = issue_image_url
            if we_vote_hosted_image_url_large is not None:
                issue_on_stage.we_vote_hosted_image_url_large = we_vote_hosted_image_url_large
            if we_vote_hosted_image_url_medium is not None:
                issue_on_stage.we_vote_hosted_image_url_medium = we_vote_hosted_image_url_medium
            if we_vote_hosted_image_url_tiny is not None:
                issue_on_stage.we_vote_hosted_image_url_tiny = we_vote_hosted_image_url_tiny
            issue_on_stage.hide_issue = hide_issue

            issue_on_stage.save()
            issue_we_vote_id = issue_on_stage.we_vote_id
            messages.add_message(request, messages.INFO, 'New issue saved.')
        else:
            messages.add_message(request, messages.INFO, 'Missing required variables.')

    url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                    "&state_code=" + str(state_code)

    if positive_value_exists(issue_we_vote_id):
        return HttpResponseRedirect(reverse('issue:issue_edit', args=(issue_we_vote_id,)) +
                                    url_variables)
    else:
        return HttpResponseRedirect(reverse('issue:issue_new', args=()) +
                                    url_variables)


@login_required
def issue_summary_view(request, issue_id):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_manager', 'political_data_viewer',
                          'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    issue_id = convert_to_int(issue_id)
    issue_on_stage_found = False
    issue_on_stage = Issue()
    try:
        issue_on_stage = Issue.objects.get(id=issue_id)
        issue_on_stage_found = True
    except Issue.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Issue.DoesNotExist:
        # This is fine, create new
        pass

    if issue_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'issue': issue_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'issue/issue_summary.html', template_values)


@login_required
def issue_delete_images_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')
    issue_we_vote_id = request.GET.get('issue_we_vote_id', '')
    url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                    "&state_code=" + str(state_code)

    if not positive_value_exists(issue_we_vote_id):
        return HttpResponseRedirect(reverse('issue:issue_new', args=()) +
                                    url_variables)
    else:
        issue_manager = IssueManager()
        results = issue_manager.retrieve_issue_from_we_vote_id(issue_we_vote_id)
        if not results['issue_found']:
            messages.add_message(request, messages.INFO, results['status'])
            return HttpResponseRedirect(reverse('issue:issue_edit', args=(issue_we_vote_id,)) +
                                        url_variables)
        issue = results['issue']
        delete_image_results = delete_cached_images_for_issue(issue)

        delete_image_count = delete_image_results['delete_image_count']
        not_deleted_image_count = delete_image_results['not_deleted_image_count']

        messages.add_message(request, messages.INFO,
                             "Images Deleted: {delete_image_count},"
                             .format(delete_image_count=delete_image_count))
        return HttpResponseRedirect(reverse('issue:issue_edit', args=(issue_we_vote_id,)) +
                                    url_variables)


@login_required
def issue_delete_process_view(request):
    """
    Delete this issue
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    issue_we_vote_id = request.POST.get('issue_we_vote_id', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))
    state_code = request.POST.get('state_code', '')

    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this issue. '
                             'Please check the checkbox to confirm you want to delete this issue.')
        return HttpResponseRedirect(reverse('issue:issue_edit', args=(issue_we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) + "&state_code=" +
                                    str(state_code))

    # Retrieve this issue
    issue_on_stage_found = False
    issue_on_stage = Issue()
    if positive_value_exists(issue_we_vote_id):
        try:
            issue_query = Issue.objects.filter(we_vote_id__iexact=issue_we_vote_id)
            if len(issue_query):
                issue_on_stage = issue_query[0]
                issue_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find issue -- exception.')

    if not issue_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find issue.')
        return HttpResponseRedirect(reverse('issue:issue_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    # Are there any positions attached to this issue that should be moved to another
    # instance of this issue?
    organization_link_to_issue_list = OrganizationLinkToIssueList()
    link_count = organization_link_to_issue_list.fetch_organization_count_for_issue(issue_we_vote_id)
    if positive_value_exists(link_count):
        organizations_found_for_this_issue = True
    else:
        organizations_found_for_this_issue = False

    if not organizations_found_for_this_issue:
        # Delete the issue
        issue_on_stage.delete()
        messages.add_message(request, messages.INFO, 'Issue deleted.')
    else:
        messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                      'organizations still attached to this issue.')
        return HttpResponseRedirect(reverse('issue:issue_edit', args=(issue_we_vote_id,)))

    return HttpResponseRedirect(reverse('issue:issue_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def organization_link_to_issue_import_from_master_server_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in ORGANIZATION_LINK_TO_ISSUE_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = organization_link_to_issue_import_from_master_server(request)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO,
                             'Organization Links import completed. '
                             'Saved: {saved}, Updated: {updated}, '
                             'Not processed: {not_processed}'
                             ''.format(saved=results['organization_link_to_issue_saved'],
                                       updated=results['organization_link_to_issue_updated'],
                                       not_processed=results['organization_link_to_issue_not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


# This page does not need to be protected.
def organization_link_to_issue_sync_out_view(request):  # organizationLinkToIssueSyncOut
    issue_search = request.GET.get('issue_search', '')

    try:
        issue_list = OrganizationLinkToIssue.objects.using('readonly').all()
        # filters = []
        # if positive_value_exists(issue_search):
        #     new_filter = Q(issue_name__icontains=issue_search)
        #     filters.append(new_filter)
        #
        #     new_filter = Q(issue_description__icontains=issue_search)
        #     filters.append(new_filter)
        #
        #     new_filter = Q(we_vote_id__icontains=issue_search)
        #     filters.append(new_filter)
        #
        #     # Add the first query
        #     if len(filters):
        #         final_filters = filters.pop()
        #
        #         # ...and "OR" the remaining items in the list
        #         for item in filters:
        #             final_filters |= item
        #
        #         issue_list = issue_list.filter(final_filters)

        issue_list_dict = issue_list.values('issue_we_vote_id', 'organization_we_vote_id',
                                            'link_active', 'reason_for_link', 'link_blocked', 'reason_link_is_blocked')
        if issue_list_dict:
            issue_list_json = list(issue_list_dict)
            return HttpResponse(json.dumps(issue_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'ORGANIZATION_LINK_TO_ISSUE_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
