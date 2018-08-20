# voter_guide/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import add_candidates_with_position_count_to_voter_guide_possibility_list, \
    add_empty_values_to_possible_candidate_dict_list, CANDIDATE_NUMBER_LIST, \
    convert_candidate_list_light_to_possible_candidates, convert_list_of_names_to_possible_candidate_dict_list, \
    extract_position_list_from_voter_guide_possibility, extract_possible_candidate_list_from_database, \
    fix_sequence_of_possible_candidate_list, \
    match_candidate_list_with_candidates_in_database, modify_one_row_in_possible_candidate_dict_list, \
    refresh_existing_voter_guides, take_in_possible_candidate_list_from_form, voter_guides_import_from_master_server
from .models import INDIVIDUAL, VoterGuide, VoterGuideListManager, VoterGuideManager, VoterGuidePossibility, \
    VoterGuidePossibilityManager
from admin_tools.views import redirect_to_sign_in_page
from candidate.controllers import retrieve_candidate_list_for_all_upcoming_elections, find_candidates_on_one_web_page
from config.base import get_environment_variable
from datetime import date, datetime, timedelta, time
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.db.models import Q
from django.shortcuts import render
from election.models import Election, ElectionManager, TIME_SPAN_LIST
from import_export_batches.models import BATCH_HEADER_MAP_FOR_POSITIONS, BatchManager, POSITION
from import_export_twitter.controllers import refresh_twitter_organization_details, scrape_social_media_from_one_site
from organization.models import Organization, OrganizationListManager, OrganizationManager
from organization.views_admin import organization_edit_process_view
from position.models import PositionEntered, PositionForFriends, PositionListManager
from twitter.models import TwitterUserManager
from voter.models import voter_has_authority, VoterManager
from wevote_functions.functions import convert_to_int, convert_date_to_we_vote_date_string, \
    extract_facebook_username_from_text_string, \
    extract_twitter_handle_from_text_string, extract_website_from_url, positive_value_exists, \
    STATE_CODE_MAP, get_voter_device_id, get_voter_api_device_id
from wevote_settings.models import RemoteRequestHistoryManager, SUGGESTED_VOTER_GUIDE_FROM_PRIOR
from django.http import HttpResponse
import json

VOTER_GUIDES_SYNC_URL = get_environment_variable("VOTER_GUIDES_SYNC_URL")  # voterGuidesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


@login_required
def create_possible_voter_guides_from_prior_elections_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    target_google_civic_election_id = 0

    limit = 3  # While in development
    status = ""
    urls_already_stored = []
    voter_guide_list = []
    voter_guides_suggested = 0

    position_list_manager = PositionListManager()
    remote_request_history_manager = RemoteRequestHistoryManager()
    voter_guide_possibility_manager = VoterGuidePossibilityManager()

    # Cycle through prior voter guides
    #  Earlier than today, but not older than 5 years ago
    today = datetime.now().date()
    we_vote_date_string_today = convert_date_to_we_vote_date_string(today)

    five_years_of_days = 5 * 365
    five_years = timedelta(days=five_years_of_days)
    five_years_ago = today - five_years
    we_vote_date_string_five_years_ago = convert_date_to_we_vote_date_string(five_years_ago)

    # Upcoming national election?
    election_manager = ElectionManager()
    if positive_value_exists(google_civic_election_id):
        status += "RETRIEVING_VOTER_GUIDES_BY_STATE_FOR_ELECTION_ID "
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            target_google_civic_election_id = election.google_civic_election_id
            status += "STATE: " + str(election.state_code) + " "
            # Get a list of all voter_guides in last 5 years
            voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.order_by('-twitter_followers_count')
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.filter(state_code__iexact=election.state_code)
            voter_guide_query = voter_guide_query.filter(election_day_text__lt=we_vote_date_string_today)
            voter_guide_query = voter_guide_query.filter(election_day_text__gte=we_vote_date_string_five_years_ago)
            voter_guide_list = list(voter_guide_query)
    else:
        status += "RETRIEVING_VOTER_GUIDES_BY_NEXT_NATIONAL_ELECTION "
        results = election_manager.retrieve_next_national_election()
        if results['election_found']:
            status += "NATIONAL_ELECTION_FOUND "
            national_election = results['election']
            target_google_civic_election_id = national_election.google_civic_election_id
            # Get a list of all voter_guides in last 5 years
            voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.order_by('-twitter_followers_count')
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.filter(election_day_text__lt=we_vote_date_string_today)
            voter_guide_query = voter_guide_query.filter(election_day_text__gte=we_vote_date_string_five_years_ago)
            voter_guide_list = list(voter_guide_query)
        else:
            status += "UPCOMING_NATIONAL_ELECTION_NOT_FOUND "

        if not positive_value_exists(len(voter_guide_list)):
            # National election not found, but upcoming state election?
            status += "RETRIEVING_VOTER_GUIDES_BY_NEXT_UPCOMING_ELECTION "
            results = election_manager.retrieve_next_election_with_state_optional()
            if results['election_found']:
                status += "UPCOMING_ELECTION_FOUND "
                election = results['election']
                target_google_civic_election_id = election.google_civic_election_id
                status += "STATE: " + str(election.state_code) + " "
                # Get a list of all voter_guides in last 5 years
                voter_guide_query = VoterGuide.objects.all()
                voter_guide_query = voter_guide_query.order_by('-twitter_followers_count')
                voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
                voter_guide_query = voter_guide_query.filter(state_code__iexact=election.state_code)
                voter_guide_query = voter_guide_query.filter(election_day_text__lt=we_vote_date_string_today)
                voter_guide_query = voter_guide_query.filter(election_day_text__gte=we_vote_date_string_five_years_ago)
                voter_guide_list = list(voter_guide_query)
            else:
                status += "UPCOMING_ELECTION_NOT_FOUND "

    if positive_value_exists(len(voter_guide_list)):
        for voter_guide in voter_guide_list:
            # Check to see if suggested entry has already been created for that org + election
            if not positive_value_exists(voter_guide.organization_we_vote_id) \
                    or not positive_value_exists(target_google_civic_election_id):
                # Do not try to proceed
                continue
            already_exists = remote_request_history_manager.remote_request_history_entry_exists(
                SUGGESTED_VOTER_GUIDE_FROM_PRIOR,
                google_civic_election_id=target_google_civic_election_id,
                organization_we_vote_id=voter_guide.organization_we_vote_id)
            if already_exists:
                # Do not create another suggested entry if one already exists
                continue
            # If not, create Suggested entry
            # Get a source URL
            voter_guide_possibility_url = ""
            limit_to_organization_we_vote_ids = [voter_guide.organization_we_vote_id]
            position_list = position_list_manager.retrieve_all_positions_for_election(
                voter_guide.google_civic_election_id,
                public_only=True,
                limit_to_organization_we_vote_ids=limit_to_organization_we_vote_ids)
            if len(position_list):
                for one_position in position_list:
                    if positive_value_exists(one_position.more_info_url):
                        voter_guide_possibility_url = one_position.more_info_url
                        break  # Break out of this position loop
            if positive_value_exists(voter_guide_possibility_url):
                if voter_guide_possibility_url in urls_already_stored:
                    continue
                updated_values = {
                    # 'organization_name': organization_name,
                    # 'organization_twitter_handle': organization_twitter_handle,
                    'organization_we_vote_id': voter_guide.organization_we_vote_id,
                    # 'voter_who_submitted_name': voter_who_submitted_name,
                    # 'voter_who_submitted_we_vote_id': voter_who_submitted_we_vote_id,
                }
                results = voter_guide_possibility_manager.update_or_create_voter_guide_possibility(
                    voter_guide_possibility_url,
                    target_google_civic_election_id=target_google_civic_election_id,
                    updated_values=updated_values,
                )
                if results['voter_guide_possibility_saved']:
                    voter_guides_suggested += 1
                    urls_already_stored.append(voter_guide_possibility_url)
                    history_results = remote_request_history_manager.create_remote_request_history_entry(
                        SUGGESTED_VOTER_GUIDE_FROM_PRIOR,
                        target_google_civic_election_id,
                        organization_we_vote_id=voter_guide.organization_we_vote_id,
                    )
                if positive_value_exists(limit):
                    # While developing we want to keep a limit on this
                    if voter_guides_suggested >= limit:
                        break

    messages.add_message(request, messages.INFO,
                         '{voter_guides_suggested} voter guides suggested for '
                         'target_google_civic_election_id: {target_google_civic_election_id}. '
                         'status: {status}'.format(
                             target_google_civic_election_id=target_google_civic_election_id,
                             voter_guides_suggested=voter_guides_suggested,
                             status=status,
                         ))
    return HttpResponseRedirect(reverse('voter_guide:voter_guide_possibility_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


# We do not require login for this page
def voter_guide_create_view(request):
    """
    Allow anyone on the internet to submit a possible voter guide for including with We Vote
    :param request:
    :return:
    """
    voter_manager = VoterManager()
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_who_submitted_name = voter.get_full_name()
        voter_who_submitted_we_vote_id = voter.we_vote_id
    else:
        voter_who_submitted_we_vote_id = ""
        voter_who_submitted_name = ""

    voter_guide_possibility_id = request.GET.get('voter_guide_possibility_id', 0)

    # Take in these values, even though they will be overwritten if we've stored a voter_guide_possibility
    ballot_items_raw = request.GET.get('ballot_items_raw', "")
    candidates_missing_from_we_vote = request.GET.get('candidates_missing_from_we_vote', "")
    cannot_find_endorsements = request.GET.get('cannot_find_endorsements', False)
    capture_detailed_comments = request.GET.get('capture_detailed_comments ', False)
    clear_organization_options = request.POST.get('clear_organization_options', False)
    hide_from_active_review = request.GET.get('hide_from_active_review', False)
    ignore_stored_positions = request.GET.get('ignore_stored_positions', False)
    internal_notes = request.GET.get('internal_notes', "")
    organization_name = request.GET.get('organization_name', "")
    organization_twitter_handle = request.GET.get('organization_twitter_handle', "")
    organization_we_vote_id = request.GET.get('organization_we_vote_id', "")
    political_data_manager = voter_has_authority(request, 'political_data_manager')
    state_code = request.GET.get('state_code', "")
    target_google_civic_election_id = request.GET.get('target_google_civic_election_id', "")
    voter_guide_possibility_url = request.GET.get('voter_guide_possibility_url', "")

    batch_header_id = 0
    display_all_done_button = False
    ignore_this_source = False
    organization = None
    organization_found = False
    positions_ready_to_save_as_batch = False
    possible_candidate_list = []
    possible_candidate_list_found = False
    if positive_value_exists(voter_guide_possibility_id):
        voter_guide_possibilities_query = VoterGuidePossibility.objects.all()
        voter_guide_possibility = voter_guide_possibilities_query.get(id=voter_guide_possibility_id)
        if positive_value_exists(voter_guide_possibility.id):
            ballot_items_raw = voter_guide_possibility.ballot_items_raw
            batch_header_id = voter_guide_possibility.batch_header_id
            candidates_missing_from_we_vote = voter_guide_possibility.candidates_missing_from_we_vote
            cannot_find_endorsements = voter_guide_possibility.cannot_find_endorsements
            capture_detailed_comments = voter_guide_possibility.capture_detailed_comments
            hide_from_active_review = voter_guide_possibility.hide_from_active_review
            ignore_stored_positions = voter_guide_possibility.ignore_stored_positions
            ignore_this_source = voter_guide_possibility.ignore_this_source
            internal_notes = voter_guide_possibility.internal_notes
            organization_name = voter_guide_possibility.organization_name
            organization_twitter_handle = voter_guide_possibility.organization_twitter_handle
            organization_we_vote_id = voter_guide_possibility.organization_we_vote_id
            positions_ready_to_save_as_batch = voter_guide_possibility.positions_ready_to_save_as_batch()
            target_google_civic_election_id = voter_guide_possibility.target_google_civic_election_id
            voter_who_submitted_we_vote_id = voter_guide_possibility.voter_who_submitted_we_vote_id
            voter_guide_possibility_url = voter_guide_possibility.voter_guide_possibility_url
            results = extract_possible_candidate_list_from_database(voter_guide_possibility)
            if results['possible_candidate_list_found']:
                possible_candidate_list = results['possible_candidate_list']
                possible_candidate_list_found = True

                google_civic_election_id_list = []
                # Match incoming candidates to candidates already in the database
                results = match_candidate_list_with_candidates_in_database(
                    possible_candidate_list, google_civic_election_id_list)
                if results['possible_candidate_list_found']:
                    possible_candidate_list = results['possible_candidate_list']

    if positive_value_exists(voter_guide_possibility_url):
        display_all_done_button = True

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    organization_list_manager = OrganizationListManager()
    organization_manager = OrganizationManager()
    organizations_list = []
    twitter_user_manager = TwitterUserManager()
    if positive_value_exists(organization_we_vote_id):
        results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if results['organization_found']:
            organization_found = True
            organization = results['organization']
            organization_name = organization.organization_name
            twitter_user_manager = TwitterUserManager()
            organization_twitter_handle = twitter_user_manager.fetch_twitter_handle_from_organization_we_vote_id(
                organization_we_vote_id)
    elif positive_value_exists(organization_name) or positive_value_exists(organization_twitter_handle) \
            and not positive_value_exists(clear_organization_options):
        # Search for organizations that match
        results = organization_list_manager.organization_search_find_any_possibilities(
            organization_name=organization_name,
            organization_twitter_handle=organization_twitter_handle
        )

        if results['organizations_found']:
            organizations_list = results['organizations_list']
            organizations_count = len(organizations_list)

            if organizations_count == 0:
                messages.add_message(request, messages.INFO, 'We did not find any organizations that match.')
            elif organizations_count == 1:
                messages.add_message(request, messages.INFO,
                                     'We found {count} organization that might match.'
                                     ''.format(count=organizations_count))
            else:
                messages.add_message(request, messages.INFO,
                                     'We found {count} organizations that might match.'
                                     ''.format(count=organizations_count))
    elif positive_value_exists(voter_guide_possibility_url) and not positive_value_exists(clear_organization_options):
        facebook_page = ""
        facebook_page_list = []
        twitter_or_facebook_found = False
        twitter_handle = ""
        twitter_handle_list = []

        retrieve_list = True
        scrape_results = scrape_social_media_from_one_site(voter_guide_possibility_url, retrieve_list)

        # Only include a change if we have a new value (do not try to save blank value)
        if scrape_results['twitter_handle_found'] and positive_value_exists(scrape_results['twitter_handle']):
            twitter_handle = scrape_results['twitter_handle']
            twitter_handle_list = scrape_results['twitter_handle_list']
            twitter_or_facebook_found = True

        if scrape_results['facebook_page_found'] and positive_value_exists(scrape_results['facebook_page']):
            facebook_page = scrape_results['facebook_page']
            facebook_page_list = scrape_results['facebook_page_list']
            twitter_or_facebook_found = True

        if twitter_or_facebook_found:
            # Search for organizations that match (by Twitter Handle)
            twitter_handle_list_modified = []
            for one_twitter_handle in twitter_handle_list:
                if positive_value_exists(one_twitter_handle):
                    one_twitter_handle = one_twitter_handle.strip()
                if positive_value_exists(one_twitter_handle):
                    twitter_handle_lower = one_twitter_handle.lower()
                    twitter_handle_lower = extract_twitter_handle_from_text_string(twitter_handle_lower)
                    if twitter_handle_lower not in twitter_handle_list_modified:
                        twitter_handle_list_modified.append(twitter_handle_lower)

            # Search for organizations that match (by Facebook page)
            facebook_page_list_modified = []
            for one_facebook_page in facebook_page_list:
                if positive_value_exists(one_facebook_page):
                    one_facebook_page = one_facebook_page.strip()
                if positive_value_exists(one_facebook_page):
                    one_facebook_page_lower = one_facebook_page.lower()
                    one_facebook_page_lower = extract_facebook_username_from_text_string(one_facebook_page_lower)
                    if one_facebook_page_lower not in facebook_page_list_modified:
                        facebook_page_list_modified.append(one_facebook_page_lower)

            # We want to create an organization for each Twitter handle we find on the page so it can be chosen below
            for one_twitter_handle in twitter_handle_list_modified:
                one_organization_found = False
                results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
                    one_twitter_handle)
                if results['twitter_link_to_organization_found']:
                    twitter_link_to_organization = results['twitter_link_to_organization']
                    organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                        twitter_link_to_organization.organization_we_vote_id)
                    if organization_results['organization_found']:
                        one_organization_found = True
                twitter_user_id = 0
                twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                    twitter_user_id, one_twitter_handle)
                if twitter_results['twitter_user_found']:
                    twitter_user = twitter_results['twitter_user']
                    twitter_user_id = twitter_user.twitter_id
                if not one_organization_found and positive_value_exists(twitter_user_id):
                    organization_name = ""
                    create_results = organization_manager.create_organization(
                        organization_name=organization_name, organization_twitter_handle=one_twitter_handle)
                    if create_results['organization_created']:
                        one_organization = create_results['organization']

                        # Create TwitterLinkToOrganization
                        link_results = twitter_user_manager.create_twitter_link_to_organization(
                            twitter_user_id, one_organization.we_vote_id)
                        # Refresh the organization with the Twitter details
                        refresh_twitter_organization_details(one_organization, twitter_user_id)

            voter_guide_website = extract_website_from_url(voter_guide_possibility_url)
            results = organization_list_manager.organization_search_find_any_possibilities(
                organization_website=voter_guide_website,
                facebook_page_list=facebook_page_list_modified,
                twitter_handle_list=twitter_handle_list_modified
            )

            if results['organizations_found']:
                organizations_list = results['organizations_list']
                organizations_count = len(organizations_list)

                if organizations_count == 0:
                    pass
                    # messages.add_message(request, messages.INFO, 'We did not find any organizations that match.')
                elif organizations_count == 1:
                    messages.add_message(request, messages.INFO,
                                         'We found {count} organization that might match.'
                                         ''.format(count=organizations_count))
                else:
                    messages.add_message(request, messages.INFO,
                                         'We found {count} organizations that might match.'
                                         ''.format(count=organizations_count))

    possible_candidate_list_modified = []
    positions_stored_count = 0
    positions_not_stored_count = 0
    for one_possible_candidate in possible_candidate_list:
        # Augment the information about the election this candidate is competing in
        if positive_value_exists(one_possible_candidate['google_civic_election_id']):
            for one_election in upcoming_election_list:
                if one_election.google_civic_election_id == one_possible_candidate['google_civic_election_id']:
                    one_possible_candidate['election_name'] = one_election.election_name
                    one_possible_candidate['election_day_text'] = one_election.election_day_text

        # Identify which candidates already have positions stored
        if positive_value_exists(organization_we_vote_id) \
                and 'candidate_we_vote_id' in one_possible_candidate \
                and positive_value_exists(one_possible_candidate['candidate_we_vote_id']):
            position_exists_query = PositionEntered.objects.filter(
                organization_we_vote_id=organization_we_vote_id,
                candidate_campaign_we_vote_id=one_possible_candidate['candidate_we_vote_id'])
            position_list = list(position_exists_query)
            if positive_value_exists(len(position_list)):
                one_possible_candidate['position_we_vote_id'] = position_list[0].we_vote_id
                positions_stored_count += 1
            else:
                positions_not_stored_count += 1

        possible_candidate_list_modified.append(one_possible_candidate)

    messages_on_stage = get_messages(request)

    template_values = {
        'ballot_items_raw':             ballot_items_raw,
        'batch_header_id':              batch_header_id,
        'candidates_missing_from_we_vote':  candidates_missing_from_we_vote,
        'cannot_find_endorsements':     cannot_find_endorsements,
        'capture_detailed_comments':    capture_detailed_comments,
        'display_all_done_button':      display_all_done_button,
        'hide_from_active_review':      hide_from_active_review,
        'ignore_stored_positions':      ignore_stored_positions,
        'ignore_this_source':           ignore_this_source,
        'internal_notes':               internal_notes,
        'messages_on_stage':            messages_on_stage,
        'organization':                 organization,
        'organization_found':           organization_found,
        'organization_name':            organization_name,
        'organization_twitter_handle':  organization_twitter_handle,
        'organization_we_vote_id':      organization_we_vote_id,
        'organizations_list':           organizations_list,
        'political_data_manager':       political_data_manager,
        'possible_candidate_list':      possible_candidate_list_modified,
        'possible_candidate_list_found': possible_candidate_list_found,
        'positions_ready_to_save_as_batch': positions_ready_to_save_as_batch,
        'positions_stored_count':       positions_stored_count,
        'positions_not_stored_count':   positions_not_stored_count,
        'state_code':                   state_code,
        'state_list':                   sorted_state_list,
        'target_google_civic_election_id':  target_google_civic_election_id,
        'upcoming_election_list':       upcoming_election_list,
        'voter_guide_possibility_id':   voter_guide_possibility_id,
        'voter_guide_possibility_url':  voter_guide_possibility_url,
        'voter_who_submitted_name':     voter_who_submitted_name,
        'voter_who_submitted_we_vote_id': voter_who_submitted_we_vote_id,
    }
    return render(request, 'voter_guide/voter_guide_create.html', template_values)


# We do not require login for this page
def voter_guide_create_process_view(request):
    """

    :param request:
    :return:
    """
    status = ""

    all_done_with_entry = request.POST.get('all_done_with_entry', 0)
    ballot_items_raw = request.POST.get('ballot_items_raw', "")
    ballot_items_additional = request.POST.get('ballot_items_additional', "")
    candidates_missing_from_we_vote = request.POST.get('candidates_missing_from_we_vote', "")
    cannot_find_endorsements = request.POST.get('cannot_find_endorsements', False)
    capture_detailed_comments = request.POST.get('capture_detailed_comments', False)
    clear_organization_options = request.POST.get('clear_organization_options', 0)
    confirm_delete = request.POST.get('confirm_delete', 0)
    form_submitted = request.POST.get('form_submitted', False)
    hide_from_active_review = request.POST.get('hide_from_active_review', False)
    ignore_stored_positions = request.POST.get('ignore_stored_positions', False)
    ignore_this_source = request.POST.get('ignore_this_source', False)
    internal_notes = request.POST.get('internal_notes', "")
    organization_name = request.POST.get('organization_name', '')
    organization_twitter_handle = request.POST.get('organization_twitter_handle', '')
    organization_we_vote_id = request.POST.get('organization_we_vote_id', None)
    scan_url_again = request.POST.get('scan_url_again', False)
    voter_guide_possibility_id = request.POST.get('voter_guide_possibility_id', 0)
    voter_guide_possibility_url = request.POST.get('voter_guide_possibility_url', '')
    voter_who_submitted_we_vote_id = request.POST.get('voter_who_submitted_we_vote_id', '')

    # Filter incoming data
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle)

    candidate_number_list = CANDIDATE_NUMBER_LIST
    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    voter_manager = VoterManager()
    voter_who_submitted_name = ""
    voter_found = False
    if not positive_value_exists(voter_who_submitted_we_vote_id):
        voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_found = True
            voter_who_submitted_name = voter.get_full_name()
            voter_who_submitted_we_vote_id = voter.we_vote_id
        else:
            voter_who_submitted_name = ""
            voter_who_submitted_we_vote_id = ""

    if not positive_value_exists(voter_who_submitted_we_vote_id):
        generate_if_no_value = True
        voter_device_id = get_voter_api_device_id(request, generate_if_no_value)
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_found = True
            voter_who_submitted_name = voter.get_full_name()
            voter_who_submitted_we_vote_id = voter.we_vote_id
        else:
            voter_who_submitted_name = ""
            voter_who_submitted_we_vote_id = ""

    if not positive_value_exists(voter_found):
        generate_if_no_value = True
        voter_device_id = get_voter_api_device_id(request, generate_if_no_value)
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_who_submitted_name = voter.get_full_name()
            voter_who_submitted_we_vote_id = voter.we_vote_id

    if not positive_value_exists(voter_guide_possibility_url) and positive_value_exists(form_submitted):
        messages.add_message(request, messages.ERROR, 'Please include a link to where you found this voter guide.')

    political_data_manager = voter_has_authority(request, 'political_data_manager')
    if positive_value_exists(political_data_manager):
        if positive_value_exists(confirm_delete):
            results = voter_guide_possibility_manager.delete_voter_guide_possibility(
                voter_guide_possibility_id=voter_guide_possibility_id)
            if results['success']:
                return HttpResponseRedirect(reverse('voter_guide:voter_guide_create', args=()))

    # #########################################
    # Figure out the Organization
    if positive_value_exists(clear_organization_options):
        organization_we_vote_id = ""
        organization_name = ""
        organization_twitter_handle = ""

    organization_manager = OrganizationManager()

    if positive_value_exists(organization_we_vote_id):
        results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if results['organization_found']:
            organization = results['organization']
            organization_name = organization.organization_name
            twitter_user_manager = TwitterUserManager()
            organization_twitter_handle = twitter_user_manager.fetch_twitter_handle_from_organization_we_vote_id(
                organization_we_vote_id)

    google_civic_election_id_list = []
    election_manager = ElectionManager()
    results = election_manager.retrieve_upcoming_elections()
    if results['election_list_found']:
        upcoming_election_list = results['election_list']
        for one_election in upcoming_election_list:
            if positive_value_exists(one_election.google_civic_election_id):
                google_civic_election_id_list.append(one_election.google_civic_election_id)

    # #########################################
    # Figure out the Possible Candidates
    changes_made = False
    possible_candidate_list = []
    possible_candidate_list_found = False

    possible_candidate_list_from_form = []
    possible_candidates_results = take_in_possible_candidate_list_from_form(request)
    if possible_candidates_results['possible_candidate_list_found']:
        possible_candidate_list_from_form = possible_candidates_results['possible_candidate_list']
        possible_candidate_list_found = True

    possible_candidate_list = possible_candidate_list + possible_candidate_list_from_form
    results = fix_sequence_of_possible_candidate_list(possible_candidate_list)
    if results['possible_candidate_list_found']:
        possible_candidate_list = results['possible_candidate_list']

    # We will need all candidates for all upcoming elections so we can search the HTML of
    #  the possible voter guide for these names
    possible_candidate_list_from_url_scan = []
    first_scan_needed = positive_value_exists(voter_guide_possibility_url) and not possible_candidate_list_found
    scan_url_now = first_scan_needed or positive_value_exists(scan_url_again)
    if scan_url_now and positive_value_exists(google_civic_election_id_list):
        results = retrieve_candidate_list_for_all_upcoming_elections(google_civic_election_id_list)
        if results['candidate_list_found']:
            candidate_list_light = results['candidate_list_light']
            candidate_scrape_results = \
                find_candidates_on_one_web_page(voter_guide_possibility_url, candidate_list_light)
            if candidate_scrape_results['at_least_one_candidate_found']:
                selected_candidate_list_light = candidate_scrape_results['selected_candidate_list_light']

                # Remove the candidates we already have in possible_candidate_list from selected_candidate_list_light
                selected_candidate_list_light_updated = []
                for one_light_possible_candidate in selected_candidate_list_light:
                    one_light_possible_candidate_is_unique = True
                    for one_possible_candidate in possible_candidate_list:
                        if one_light_possible_candidate['candidate_we_vote_id'] == \
                                one_possible_candidate['candidate_we_vote_id']:
                            one_light_possible_candidate_is_unique = False
                            break
                    if one_light_possible_candidate_is_unique:
                        selected_candidate_list_light_updated.append(one_light_possible_candidate)

                possible_candidates_results = convert_candidate_list_light_to_possible_candidates(
                    selected_candidate_list_light_updated)
                if possible_candidates_results['possible_candidate_list_found']:
                    possible_candidate_list_from_url_scan = possible_candidates_results['possible_candidate_list']
                    possible_candidate_list_found = True

    possible_candidate_list = possible_candidate_list + possible_candidate_list_from_url_scan
    results = fix_sequence_of_possible_candidate_list(possible_candidate_list)
    if results['possible_candidate_list_found']:
        possible_candidate_list = results['possible_candidate_list']

    # If we don't already have a list of possible candidates, check the raw text entry field
    possible_candidate_list_from_ballot_items_raw = []
    if not possible_candidate_list_found and positive_value_exists(ballot_items_raw):
        results = break_up_text_into_possible_candidates_list(ballot_items_raw)
        if results['possible_candidate_list_found']:
            possible_candidate_list_from_ballot_items_raw = results['possible_candidate_list']
            # possible_candidate_list_found = True
            changes_made = True

    possible_candidate_list = possible_candidate_list + possible_candidate_list_from_ballot_items_raw
    results = fix_sequence_of_possible_candidate_list(possible_candidate_list)
    if results['possible_candidate_list_found']:
        possible_candidate_list = results['possible_candidate_list']

    # If the "remove" link was clicked, remove that entry from the possible
    number_index = 0
    row_index_to_remove = None
    for candidate_number in candidate_number_list:
        if number_index >= len(candidate_number_list):
            break
        if positive_value_exists(request.POST.get('remove_possible_candidate_' +
                                                  candidate_number_list[number_index], 0)):
            # A request to remove this row was found
            row_index_to_remove = candidate_number_list[number_index]
            # Only remove one at a time
            break
        number_index += 1

    if row_index_to_remove is not None:
        results = modify_one_row_in_possible_candidate_dict_list(possible_candidate_list, row_index_to_remove)
        if positive_value_exists(results['possible_candidate_list_found']):
            possible_candidate_list = results['possible_candidate_list']

    # Check for additional items to add
    if positive_value_exists(ballot_items_additional):
        number_of_current_possible_candidates = len(possible_candidate_list)
        # The index of candidate_number_list is always 1 below the candidate_number we
        # want (index = 0, candidate_number = "001"). So if there are 3 possible candidates, the last candidate_number
        # in use will be "003". To get "004" for the next possible candidate, we pass in the index "3"
        try:
            next_index = number_of_current_possible_candidates
            starting_candidate_number = candidate_number_list[next_index]  # This returns a string like "004"
            results = break_up_text_into_possible_candidates_list(ballot_items_additional, starting_candidate_number)
            if results['possible_candidate_list_found']:
                additional_possible_candidate_list = results['possible_candidate_list']
                possible_candidate_list = possible_candidate_list + additional_possible_candidate_list
                results = fix_sequence_of_possible_candidate_list(possible_candidate_list)
                if results['possible_candidate_list_found']:
                    possible_candidate_list = results['possible_candidate_list']
                changes_made = True
        except Exception as e:
            # If the next index is outside the candidate_number_list then we don't want to take in new candidates
            pass

    # Match incoming candidates to candidates already in the database
    if len(possible_candidate_list):
        results = match_candidate_list_with_candidates_in_database(possible_candidate_list,
                                                                   google_civic_election_id_list)
        if results['possible_candidate_list_found']:
            possible_candidate_list = results['possible_candidate_list']

        if positive_value_exists(ignore_stored_positions):
            # Identify which candidates already have positions stored, and remove them
            altered_position_list = []
            altered_position_list_used = False
            for one_possible_candidate in possible_candidate_list:
                does_not_contain_position = True
                if positive_value_exists(organization_we_vote_id) \
                        and 'candidate_we_vote_id' in one_possible_candidate \
                        and positive_value_exists(one_possible_candidate['candidate_we_vote_id']):
                    position_exists_query = PositionEntered.objects.filter(
                        organization_we_vote_id=organization_we_vote_id,
                        candidate_campaign_we_vote_id=one_possible_candidate['candidate_we_vote_id'])
                    position_list = list(position_exists_query)
                    if positive_value_exists(len(position_list)):
                        # Since there is a position, remove this possible candidate
                        altered_position_list_used = True
                        does_not_contain_position = False
                        pass
                if does_not_contain_position:
                    altered_position_list.append(one_possible_candidate)

            if altered_position_list_used:
                results = fix_sequence_of_possible_candidate_list(altered_position_list)
                if results['possible_candidate_list_found']:
                    possible_candidate_list = results['possible_candidate_list']

    # Add empty values above and beyond the values in possible_candidate_list so we overwrite (remove)
    #  data that might have already been stored in the database
    number_of_current_possible_candidates = len(possible_candidate_list)
    # The index of candidate_number_list is always 1 below the candidate_number we
    # want (index = 0, candidate_number = "001"). So if there are 3 possible candidates, the last candidate_number
    # in use will be "003". To get "004" for the next possible candidate, we pass in the index "3"
    next_index = number_of_current_possible_candidates
    try:
        starting_candidate_number = candidate_number_list[next_index]  # This returns a string like "004"
        results = add_empty_values_to_possible_candidate_dict_list(starting_candidate_number)
        if results['possible_candidate_list_found']:
            additional_possible_candidate_list = results['possible_candidate_list']
            possible_candidate_list = possible_candidate_list + additional_possible_candidate_list
    except Exception as e:
        # If the next index is outside the candidate_number_list then we don't want to add empty candidates
        pass

    # Now save the possibility so far
    if positive_value_exists(voter_guide_possibility_url):
        # display_all_done_button = True
        updated_values = {
            'ballot_items_raw':                 ballot_items_raw,
            'organization_name':                organization_name,
            'organization_twitter_handle':      organization_twitter_handle,
            'organization_we_vote_id':          organization_we_vote_id,
            'voter_guide_possibility_url':      voter_guide_possibility_url,
            'voter_who_submitted_name':         voter_who_submitted_name,
            'voter_who_submitted_we_vote_id':   voter_who_submitted_we_vote_id,
        }
        if political_data_manager:
            updated_values['ignore_stored_positions'] = ignore_stored_positions
            updated_values['ignore_this_source'] = ignore_this_source
            updated_values['internal_notes'] = internal_notes
            updated_values['candidates_missing_from_we_vote'] = candidates_missing_from_we_vote
            updated_values['cannot_find_endorsements'] = cannot_find_endorsements
            updated_values['capture_detailed_comments'] = capture_detailed_comments
            updated_values['hide_from_active_review'] = hide_from_active_review

        for one_possible_candidate in possible_candidate_list:
            if 'possible_candidate_number' in one_possible_candidate \
                    and positive_value_exists(one_possible_candidate['possible_candidate_number']):
                updated_values['candidate_name_' + one_possible_candidate['possible_candidate_number']] = \
                    one_possible_candidate['candidate_name']
                updated_values['candidate_we_vote_id_' + one_possible_candidate['possible_candidate_number']] = \
                    one_possible_candidate['candidate_we_vote_id']
                updated_values['comment_about_candidate_' + one_possible_candidate['possible_candidate_number']] = \
                    one_possible_candidate['comment_about_candidate']
                updated_values['google_civic_election_id_' + one_possible_candidate['possible_candidate_number']] = \
                    convert_to_int(one_possible_candidate['google_civic_election_id'])
                updated_values['stance_about_candidate_' + one_possible_candidate['possible_candidate_number']] = \
                    one_possible_candidate['stance_about_candidate']
        results = voter_guide_possibility_manager.update_or_create_voter_guide_possibility(
            voter_guide_possibility_url,
            voter_guide_possibility_id=voter_guide_possibility_id,
            updated_values=updated_values)
        if not positive_value_exists(results['success']):
            status += results['status']
            messages.add_message(request, messages.ERROR, 'Could not save this suggested voter guide. '
                                                          'STATUS: {status}'.format(status=status))

        voter_guide_possibility_id = results['voter_guide_possibility_id']

    if all_done_with_entry:
        messages.add_message(request, messages.SUCCESS,
                             'Thanks for adding this voter guide! Would you like to add another?')
        return HttpResponseRedirect(reverse('voter_guide:voter_guide_create', args=()))

    if positive_value_exists(form_submitted) and positive_value_exists(changes_made):
        messages.add_message(request, messages.SUCCESS, 'Changes saved.')

    return HttpResponseRedirect(reverse('voter_guide:voter_guide_create', args=()) +
                                "?voter_guide_possibility_id=" + str(voter_guide_possibility_id))


def break_up_text_into_possible_candidates_list(ballot_items, starting_candidate_number="001"):
    names_list = []
    # First break up multiple lines
    ballot_items_list1 = ballot_items.splitlines()
    for one_line in ballot_items_list1:
        # Then break up by comma
        ballot_items_list2 = one_line.split(",")
        for one_item in ballot_items_list2:
            one_item_stripped = one_item.strip()
            if positive_value_exists(one_item_stripped):
                names_list.append(one_item_stripped)

    possible_candidates_results = \
        convert_list_of_names_to_possible_candidate_dict_list(names_list, starting_candidate_number)

    results = {
        'status': possible_candidates_results['status'],
        'success': possible_candidates_results['success'],
        'possible_candidate_list': possible_candidates_results['possible_candidate_list'],
        'possible_candidate_list_found': possible_candidates_results['possible_candidate_list_found'],
    }
    return results


# This page does not need to be protected.
def voter_guides_sync_out_view(request):  # voterGuidesSyncOut
    status = ""
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    try:
        voter_guide_query = VoterGuide.objects.using('readonly').all()
        voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
        if positive_value_exists(google_civic_election_id):
            voter_guide_query = voter_guide_query.filter(google_civic_election_id=google_civic_election_id)

        # serializer = VoterGuideSerializer(voter_guide_list, many=True)
        # return Response(serializer.data)
        voter_guide_query = voter_guide_query.extra(
            select={'last_updated': "to_char(last_updated, 'YYYY-MM-DD HH24:MI:SS')"})
        # Removed: 'vote_smart_time_span',
        voter_guide_query = voter_guide_query.values('we_vote_id', 'display_name', 'google_civic_election_id',
                                                     'election_day_text',
                                                     'image_url', 'last_updated', 'organization_we_vote_id',
                                                     'owner_we_vote_id', 'pledge_count', 'pledge_goal',
                                                     'public_figure_we_vote_id',
                                                     'twitter_description', 'twitter_followers_count',
                                                     'twitter_handle',
                                                     'voter_guide_owner_type',
                                                     'we_vote_hosted_profile_image_url_large',
                                                     'we_vote_hosted_profile_image_url_medium',
                                                     'we_vote_hosted_profile_image_url_tiny')
        voter_guide_list_dict = list(voter_guide_query)
        return HttpResponse(json.dumps(voter_guide_list_dict), content_type='application/json')
    except Exception as e:
        status += 'VOTER_GUIDE_QUERY_PROBLEM ' + str(e) + ' '

    status += 'VOTER_GUIDE_LIST_MISSING'
    json_data = {
        'success': False,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def voter_guides_import_from_master_server_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in VOTER_GUIDES_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = voter_guides_import_from_master_server(request, google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Voter Guides import completed. '
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
def generate_voter_guide_possibility_batch_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    voter_guide_possibility_id = request.GET.get('voter_guide_possibility_id', 0)

    position_list_ready = False
    structured_json_list = []
    voter_guide_possibility_found = False
    voter_guide_possibility_list = []
    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    import_export_batch_manager = BatchManager()
    batch_header_id = 0
    batch_rows_count = 0

    results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(voter_guide_possibility_id)
    if results['voter_guide_possibility_found']:
        voter_guide_possibility_found = True
        voter_guide_possibility = results['voter_guide_possibility']
        voter_guide_possibility_list.append(voter_guide_possibility)

    if voter_guide_possibility_found:
        # Create structured_json_list with all of the positions we want to save
        for one_voter_guide_possibility in voter_guide_possibility_list:
            results = extract_position_list_from_voter_guide_possibility(one_voter_guide_possibility)
            if results['position_json_list_found']:
                position_list_ready = True
                structured_json_list += results['position_json_list']

    if position_list_ready:
        file_name = "Voter Guide Possibility "
        if positive_value_exists(voter_guide_possibility_id):
            file_name += "" + str(voter_guide_possibility_id)
        results = import_export_batch_manager.create_batch_from_json(
            file_name, structured_json_list, BATCH_HEADER_MAP_FOR_POSITIONS, POSITION,
            google_civic_election_id=google_civic_election_id)
        batch_rows_count = results['number_of_batch_rows']
        batch_header_id = results['batch_header_id']

    if voter_guide_possibility_found and positive_value_exists(batch_header_id):
        try:
            voter_guide_possibility.batch_header_id = batch_header_id
            # We do not want to hide after an import. There is often work to do after we have done the first import.
            # voter_guide_possibility.hide_from_active_review = True
            voter_guide_possibility.save()
            status += "GENERATE_VOTER_GUIDE_POSSIBILITY_BATCH-STATUS_SAVED "
        except Exception as e:
            status += "GENERATE_VOTER_GUIDE_POSSIBILITY_BATCH-FAILED_TO_SAVE_STATUS: " + str(e)

    if positive_value_exists(batch_rows_count) and positive_value_exists(batch_header_id):
        messages.add_message(request, messages.INFO,
                             '{batch_rows_count} positions to be imported '
                             'from voter guide possibilities. '
                             ''.format(batch_rows_count=batch_rows_count))

        return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                    '?batch_header_id=' + str(batch_header_id) +
                                    '&kind_of_batch=' + str(POSITION) +
                                    '&google_civic_election_id=' + str(google_civic_election_id))
    else:
        messages.add_message(request, messages.ERROR,
                             'There has been a problem importing positions '
                             'from voter guide possibilities. ')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    '?kind_of_batch=' + str(POSITION) +
                                    '&google_civic_election_id=' + str(google_civic_election_id))


@login_required
def generate_voter_guides_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_guide_stored_for_this_organization = {}
    # voter_guide_stored_for_this_public_figure = []
    # voter_guide_stored_for_this_voter = []

    voter_guide_created_count = 0
    voter_guide_updated_count = 0

    # What elections do we want to generate voter_guides for?
    election_list = Election.objects.all()
    voter_guide_manager = VoterGuideManager()

    # Cycle through organizations
    organization_list = Organization.objects.all()
    for organization in organization_list:
        # Cycle through elections. Find out position count for this org for each election.
        # If > 0, then create a voter_guide entry
        for election in election_list:
            # Make sure we have the organization in this dict
            if organization.we_vote_id not in voter_guide_stored_for_this_organization:
                voter_guide_stored_for_this_organization[organization.we_vote_id] = []
            if election.google_civic_election_id in voter_guide_stored_for_this_organization[organization.we_vote_id]:
                # If we already have a voter guide for this election for this organization, then keep going
                continue

            # organization hasn't had voter guides stored yet.
            # Search for positions with this organization_id and google_civic_election_id
            google_civic_election_id = str(election.google_civic_election_id)  # Convert to VarChar

            # As of August 2018 exclude Vote Smart ratings (vote_smart_rating__isnull)
            positions_exist_query = PositionEntered.objects.filter(
                organization_id=organization.id,
                google_civic_election_id=google_civic_election_id)
            positions_exist_query = positions_exist_query.filter(
                Q(vote_smart_rating__isnull=True) | Q(vote_smart_rating=""))
            positions_count = positions_exist_query.count()
            if positions_count > 0:
                voter_guide_we_vote_id = ''
                results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                    voter_guide_we_vote_id, organization.we_vote_id, election.google_civic_election_id)
                if results['success']:
                    if results['new_voter_guide_created']:
                        voter_guide_created_count += 1
                    else:
                        voter_guide_updated_count += 1
                voter_guide_stored_for_this_organization[organization.we_vote_id].append(google_civic_election_id)

    messages.add_message(request, messages.INFO,
                         '{voter_guide_created_count} voter guides created, '
                         '{voter_guide_updated_count} updated.'.format(
                             voter_guide_created_count=voter_guide_created_count,
                             voter_guide_updated_count=voter_guide_updated_count,
                         ))
    return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()))


@login_required
def label_vote_smart_voter_guides_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_guide_labeled_count = 0
    voter_guide_not_labeled_count = 0

    # Cycle through existing voter guides
    voter_guide_query = VoterGuide.objects.all()
    voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
    voter_guide_list = list(voter_guide_query)
    for voter_guide in voter_guide_list:
        # Only look at voter guides attached to an election
        if positive_value_exists(voter_guide.google_civic_election_id):
            # Are there positions for this organization for this election?
            positions_count = PositionEntered.objects.filter(
                organization_we_vote_id=voter_guide.organization_we_vote_id,
                google_civic_election_id=voter_guide.google_civic_election_id).count()
            if positive_value_exists(positions_count):
                # If the total number of positions that exist is the same number of vote smart positions, then we
                # know that ALL positions are vote smart positions

                # Find the count of Vote Smart ratings
                positions_exist_query = PositionEntered.objects.filter(
                    organization_we_vote_id=voter_guide.organization_we_vote_id,
                    google_civic_election_id=voter_guide.google_civic_election_id)
                positions_exist_query = positions_exist_query.filter(vote_smart_rating__isnull=False)
                positions_exist_query = positions_exist_query.exclude(vote_smart_rating="")
                vote_smart_positions_count = positions_exist_query.count()
                if vote_smart_positions_count == positions_count:
                    # If all of the positions have a positive value in "vote_smart_rating", then label the voter
                    # guide as "vote_smart_ratings_only"
                    voter_guide.vote_smart_ratings_only = True
                    voter_guide.save()
                    voter_guide_labeled_count += 1

    messages.add_message(request, messages.INFO,
                         '{voter_guide_labeled_count} voter guides labeled.'.format(
                             voter_guide_labeled_count=voter_guide_labeled_count,
                         ))
    return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()))


@login_required
def generate_voter_guides_for_one_election_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR,
                             'Cannot generate voter guides for one election: google_civic_election_id missing')
        return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()))

    voter_guide_stored_for_this_organization = []
    # voter_guide_stored_for_this_public_figure = []
    # voter_guide_stored_for_this_voter = []

    voter_guide_created_count = 0
    voter_guide_updated_count = 0

    # What elections do we want to generate voter_guides for?
    election_list = Election.objects.all()

    # Cycle through organizations
    organization_list = Organization.objects.all()
    for organization in organization_list:
        # Cycle through elections. Find out position count for this org for each election.
        # If > 0, then create a voter_guide entry
        if organization.we_vote_id not in voter_guide_stored_for_this_organization:
            # organization hasn't had voter guides stored yet in this run through.
            # Search for positions with this organization_id and google_civic_election_id

            # As of August 2018 exclude Vote Smart ratings (vote_smart_rating__isnull)
            positions_exist_query = PositionEntered.objects.filter(
                organization_we_vote_id=organization.we_vote_id,
                google_civic_election_id=google_civic_election_id)
            positions_exist_query = positions_exist_query.filter(
                Q(vote_smart_rating__isnull=True) | Q(vote_smart_rating=""))
            positions_count = positions_exist_query.count()
            if positions_count > 0:
                # We have found positions (not including Vote Smart ratings)
                voter_guide_manager = VoterGuideManager()
                voter_guide_we_vote_id = ''
                results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                    voter_guide_we_vote_id, organization.we_vote_id, google_civic_election_id)
                if results['success']:
                    if results['new_voter_guide_created']:
                        voter_guide_created_count += 1
                    else:
                        voter_guide_updated_count += 1

            voter_guide_stored_for_this_organization.append(organization.we_vote_id)

    messages.add_message(request, messages.INFO,
                         '{voter_guide_created_count} voter guides created, '
                         '{voter_guide_updated_count} updated.'.format(
                             voter_guide_created_count=voter_guide_created_count,
                             voter_guide_updated_count=voter_guide_updated_count,
                         ))
    return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def refresh_existing_voter_guides_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    organization_we_vote_id = request.GET.get('organization_we_vote_id', False)

    results = refresh_existing_voter_guides(google_civic_election_id, organization_we_vote_id)
    voter_guide_updated_count = results['voter_guide_updated_count']

    messages.add_message(request, messages.INFO,
                         '{voter_guide_updated_count} voter guide(s) updated.'.format(
                             voter_guide_updated_count=voter_guide_updated_count,
                         ))
    if positive_value_exists(organization_we_vote_id):
        return HttpResponseRedirect(reverse('organization:organization_we_vote_id_position_list',
                                            args=(organization_we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id)
                                    )
    else:
        return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&organization_we_vote_id=" + str(organization_we_vote_id)
                                    )


@login_required
def voter_guide_edit_view(request, voter_guide_id=0, voter_guide_we_vote_id=""):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    # voter_guide_name = request.GET.get('voter_guide_name', False)
    # google_civic_candidate_name = request.GET.get('google_civic_candidate_name', False)
    # candidate_twitter_handle = request.GET.get('candidate_twitter_handle', False)
    # candidate_url = request.GET.get('candidate_url', False)
    # party = request.GET.get('party', False)
    # ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', False)
    # ballotpedia_candidate_id = request.GET.get('ballotpedia_candidate_id', False)
    # ballotpedia_candidate_name = request.GET.get('ballotpedia_candidate_name', False)
    # ballotpedia_candidate_url = request.GET.get('ballotpedia_candidate_url', False)
    # vote_smart_id = request.GET.get('vote_smart_id', False)
    # maplight_id = request.GET.get('maplight_id', False)
    # state_code = request.GET.get('state_code', "")
    # show_all_google_search_users = request.GET.get('show_all_google_search_users', False)
    # show_all_twitter_search_results = request.GET.get('show_all_twitter_search_results', False)

    messages_on_stage = get_messages(request)
    voter_guide_id = convert_to_int(voter_guide_id)
    voter_guide_on_stage_found = False
    voter_guide_on_stage = VoterGuide()
    contest_office_id = 0
    google_civic_election_id = 0

    try:
        if positive_value_exists(voter_guide_id):
            voter_guide_on_stage = VoterGuide.objects.get(id=voter_guide_id)
        else:
            voter_guide_on_stage = VoterGuide.objects.get(we_vote_id=voter_guide_we_vote_id)
        voter_guide_on_stage_found = True
        voter_guide_id = voter_guide_on_stage.id
        google_civic_election_id = voter_guide_on_stage.google_civic_election_id
    except VoterGuide.MultipleObjectsReturned as e:
        pass
    except VoterGuide.DoesNotExist:
        # This is fine, create new below
        pass

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'voter_guide':                      voter_guide_on_stage,
        'google_civic_election_id':         google_civic_election_id,
        # Incoming variables, not saved yet
        # 'voter_guide_name':                   voter_guide_name,
    }
    return render(request, 'voter_guide/voter_guide_edit.html', template_values)


@login_required
def voter_guide_edit_process_view(request):  # NOTE: THIS FORM DOESN'T SAVE YET -- VIEW ONLY
    """
    Process the new or edit voter_guide forms
    NOTE: We are using "voter_guide_search_process_view" instead
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_guide_id = convert_to_int(request.POST['voter_guide_id'])
    redirect_to_voter_guide_list = convert_to_int(request.POST['redirect_to_voter_guide_list'])
    voter_guide_name = request.POST.get('voter_guide_name', False)
    voter_guide_twitter_handle = request.POST.get('voter_guide_twitter_handle', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    voter_guide_url = request.POST.get('voter_guide_url', False)
    state_code = request.POST.get('state_code', False)

    # Check to see if this voter_guide is already being used anywhere
    voter_guide_on_stage_found = False
    voter_guide_on_stage = VoterGuide()
    if positive_value_exists(voter_guide_id):
        try:
            voter_guide_query = VoterGuide.objects.filter(id=voter_guide_id)
            if len(voter_guide_query):
                voter_guide_on_stage = voter_guide_query[0]
                voter_guide_on_stage_found = True
        except Exception as e:
            pass

    election_manager = ElectionManager()
    election_results = election_manager.retrieve_election(google_civic_election_id)
    state_code_from_election = ""
    if election_results['election_found']:
        election = election_results['election']
        election_found = election_results['election_found']
        state_code_from_election = election.get_election_state()

    best_state_code = state_code_from_election if positive_value_exists(state_code_from_election) \
        else state_code

    try:
        if voter_guide_on_stage_found:
            # Update
            if voter_guide_name is not False:
                voter_guide_on_stage.voter_guide_name = voter_guide_name
            if voter_guide_twitter_handle is not False:
                voter_guide_on_stage.voter_guide_twitter_handle = voter_guide_twitter_handle
            if voter_guide_url is not False:
                voter_guide_on_stage.voter_guide_url = voter_guide_url

            voter_guide_on_stage.save()

            # Now refresh the cache entries for this voter_guide

            messages.add_message(request, messages.INFO, 'Candidate Campaign updated.')
        else:
            # Create new
            # election must be found
            if not election_found:
                messages.add_message(request, messages.ERROR, 'Could not find election -- required to save voter_guide.')
                return HttpResponseRedirect(reverse('voter_guide:voter_guide_edit', args=(voter_guide_id,)))

            required_voter_guide_variables = True \
                if positive_value_exists(voter_guide_name) and positive_value_exists(contest_office_id) \
                else False
            if required_voter_guide_variables:
                voter_guide_on_stage = VoterGuide(
                    voter_guide_name=voter_guide_name,
                    google_civic_election_id=google_civic_election_id,
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    state_code=best_state_code,
                )
                if voter_guide_url is not False:
                    voter_guide_on_stage.voter_guide_url = voter_guide_url

                voter_guide_on_stage.save()
                voter_guide_id = voter_guide_on_stage.id
                messages.add_message(request, messages.INFO, 'New voter_guide saved.')
            else:
                # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
                url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                                "&voter_guide_name=" + str(voter_guide_name) + \
                                "&state_code=" + str(state_code) + \
                                "&google_civic_voter_guide_name=" + str(google_civic_voter_guide_name) + \
                                "&contest_office_id=" + str(contest_office_id) + \
                                "&voter_guide_twitter_handle=" + str(voter_guide_twitter_handle) + \
                                "&voter_guide_url=" + str(voter_guide_url) + \
                                "&party=" + str(party) + \
                                "&ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                                "&ballotpedia_voter_guide_id=" + str(ballotpedia_voter_guide_id) + \
                                "&ballotpedia_voter_guide_name=" + str(ballotpedia_voter_guide_name) + \
                                "&ballotpedia_voter_guide_url=" + str(ballotpedia_voter_guide_url) + \
                                "&vote_smart_id=" + str(vote_smart_id) + \
                                "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                                "&maplight_id=" + str(maplight_id)
                if positive_value_exists(voter_guide_id):
                    return HttpResponseRedirect(reverse('voter_guide:voter_guide_edit', args=(voter_guide_id,)) +
                                                url_variables)
                else:
                    return HttpResponseRedirect(reverse('voter_guide:voter_guide_new', args=()) +
                                                url_variables)

    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save voter_guide.')
        return HttpResponseRedirect(reverse('voter_guide:voter_guide_edit', args=(voter_guide_id,)))

    if redirect_to_voter_guide_list:
        return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    return HttpResponseRedirect(reverse('voter_guide:voter_guide_edit', args=(voter_guide_id,)))


@login_required
def voter_guide_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    show_individuals = request.GET.get('show_individuals', False)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all_elections = request.GET.get('show_all_elections', False)
    state_code = request.GET.get('state_code', '')
    voter_guide_search = request.GET.get('voter_guide_search', '')

    voter_guide_list = []
    voter_guide_list_object = VoterGuideListManager()

    order_by = "google_civic_election_id"
    limit_number = 75
    results = voter_guide_list_object.retrieve_all_voter_guides_order_by(
        order_by, limit_number, voter_guide_search, google_civic_election_id, show_individuals)

    if results['success']:
        voter_guide_list = results['voter_guide_list']

    modified_voter_guide_list = []
    position_list_manager = PositionListManager()
    for one_voter_guide in voter_guide_list:
        # How many Publicly visible positions are there in this election on this voter guide?
        retrieve_public_positions = True
        one_voter_guide.number_of_public_positions = position_list_manager.fetch_positions_count_for_voter_guide(
            one_voter_guide.organization_we_vote_id, one_voter_guide.google_civic_election_id, state_code,
            retrieve_public_positions)
        # How many Friends-only visible positions are there in this election on this voter guide?
        retrieve_public_positions = False
        one_voter_guide.number_of_friends_only_positions = position_list_manager.fetch_positions_count_for_voter_guide(
            one_voter_guide.organization_we_vote_id, one_voter_guide.google_civic_election_id, state_code,
            retrieve_public_positions)
        modified_voter_guide_list.append(one_voter_guide)

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

    voter_guide_query = VoterGuide.objects.all()
    voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
    if positive_value_exists(google_civic_election_id):
        voter_guide_query = voter_guide_query.filter(google_civic_election_id=google_civic_election_id)
    if not positive_value_exists(show_individuals):
        voter_guide_query = voter_guide_query.exclude(voter_guide_owner_type__iexact=INDIVIDUAL)
    voter_guides_count = voter_guide_query.count()

    messages.add_message(request, messages.INFO, 'We found {voter_guides_count} existing voter guides. '
                                                 ''.format(voter_guides_count=voter_guides_count))

    messages_on_stage = get_messages(request)
    template_values = {
        'election_list':            election_list,
        'show_individuals':         show_individuals,
        'google_civic_election_id': google_civic_election_id,
        'show_all_elections':       show_all_elections,
        'state_code':               state_code,
        'messages_on_stage':        messages_on_stage,
        'voter_guide_list':         modified_voter_guide_list,
        'voter_guide_search':       voter_guide_search,
    }
    return render(request, 'voter_guide/voter_guide_list.html', template_values)


@login_required
def voter_guide_possibility_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all_elections = request.GET.get('show_all_elections', False)
    show_candidates_missing_from_we_vote = request.GET.get('show_candidates_missing_from_we_vote', False)
    show_cannot_find_endorsements = request.GET.get('show_cannot_find_endorsements', False)
    show_only_hide_from_active_review = request.GET.get('show_only_hide_from_active_review', False)
    state_code = request.GET.get('state_code', '')
    voter_guide_possibility_search = request.GET.get('voter_guide_possibility_search', '')

    voter_guide_possibility_archive_list = []
    voter_guide_possibility_list = []
    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    election_manager = ElectionManager()

    limit_number = 75

    # Possibilities to review
    filtered_by_title = ""
    if positive_value_exists(show_cannot_find_endorsements):
        filtered_by_title = "Endorsements Not Available Yet"
        cannot_find_endorsements = True
        order_by = "-id"
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_list(
            order_by, limit_number, voter_guide_possibility_search, google_civic_election_id,
            cannot_find_endorsements=cannot_find_endorsements)
        if results['success']:
            voter_guide_possibility_list = results['voter_guide_possibility_list']
            voter_guide_possibility_list = \
                add_candidates_with_position_count_to_voter_guide_possibility_list(voter_guide_possibility_list)
    elif positive_value_exists(show_candidates_missing_from_we_vote):
        filtered_by_title = "Candidates or Measures Missing"
        candidates_missing_from_we_vote = True
        order_by = "-id"
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_list(
            order_by, limit_number, voter_guide_possibility_search, google_civic_election_id,
            candidates_missing_from_we_vote=candidates_missing_from_we_vote)
        if results['success']:
            voter_guide_possibility_list = results['voter_guide_possibility_list']
            voter_guide_possibility_list = \
                add_candidates_with_position_count_to_voter_guide_possibility_list(voter_guide_possibility_list)
    elif positive_value_exists(show_only_hide_from_active_review):
        # Entries we've already reviewed
        filtered_by_title = "Archived"
        hide_from_active_review = True
        order_by = "-date_last_changed"
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_list(
            order_by, limit_number, voter_guide_possibility_search, google_civic_election_id,
            hide_from_active_review=hide_from_active_review)
        if results['success']:
            voter_guide_possibility_list = results['voter_guide_possibility_list']
            voter_guide_possibility_list = \
                add_candidates_with_position_count_to_voter_guide_possibility_list(voter_guide_possibility_list)
    else:
        # Entries we've already reviewed
        filtered_by_title = "To Review"
        order_by = "-id"
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_list(
            order_by, limit_number, voter_guide_possibility_search, google_civic_election_id)
        if results['success']:
            voter_guide_possibility_list = results['voter_guide_possibility_list']
            voter_guide_possibility_list = \
                add_candidates_with_position_count_to_voter_guide_possibility_list(voter_guide_possibility_list)

    # Now populate the election drop down
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

    # voter_guide_possibilities_count = len(voter_guide_possibility_list)
    #
    # messages.add_message(request, messages.INFO,
    #                      'We found {voter_guide_possibilities_count} existing voter guide possibilities. '
    #                      ''.format(voter_guide_possibilities_count=voter_guide_possibilities_count))

    messages_on_stage = get_messages(request)
    template_values = {
        'election_list':                        election_list,
        'filtered_by_title':                    filtered_by_title,
        'google_civic_election_id':             google_civic_election_id,
        'show_all_elections':                   show_all_elections,
        'show_candidates_missing_from_we_vote': show_candidates_missing_from_we_vote,
        'show_cannot_find_endorsements':        show_cannot_find_endorsements,
        'show_only_hide_from_active_review':    show_only_hide_from_active_review,
        'state_code':                           state_code,
        'messages_on_stage':                    messages_on_stage,
        'voter_guide_possibility_list':         voter_guide_possibility_list,
        'voter_guide_possibility_search':       voter_guide_possibility_search,
    }
    return render(request, 'voter_guide/voter_guide_possibility_list.html', template_values)


@login_required
def voter_guide_search_view(request):
    """
    Before creating a voter guide, search for an existing organization
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # A positive value in google_civic_election_id means we want to create a voter guide for this org for this election
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")

    messages_on_stage = get_messages(request)

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'messages_on_stage': messages_on_stage,
        'upcoming_election_list':   upcoming_election_list,
        'google_civic_election_id': google_civic_election_id,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'voter_guide/voter_guide_search.html', template_values)


@login_required
def voter_guide_search_process_view(request):
    """
    Process the new or edit organization forms
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    add_organization_button = request.POST.get('add_organization_button', False)
    if add_organization_button:
        return organization_edit_process_view(request)

    organization_name = request.POST.get('organization_name', '')
    organization_twitter_handle = request.POST.get('organization_twitter_handle', '')
    organization_facebook = request.POST.get('organization_facebook', '')
    organization_website = request.POST.get('organization_website', '')
    state_code = request.POST.get('state_code', "")

    # Save this variable so we have it on the "Add New Position" page
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)

    # Filter incoming data
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle)

    # Search for organizations that match
    organization_email = ''
    organization_list_manager = OrganizationListManager()
    results = organization_list_manager.organization_search_find_any_possibilities(
        organization_name, organization_twitter_handle, organization_website, organization_email,
        organization_facebook)

    if results['organizations_found']:
        organizations_list = results['organizations_list']
        organizations_count = len(organizations_list)

        messages.add_message(request, messages.INFO, 'We found {count} existing organization(s) '
                                                     'that might match.'.format(count=organizations_count))
    else:
        organizations_list = []
        messages.add_message(request, messages.INFO, 'No voter guides found with those search terms. '
                                                     'Please try again. ')

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    messages_on_stage = get_messages(request)
    template_values = {
        'google_civic_election_id':     google_civic_election_id,
        'messages_on_stage':            messages_on_stage,
        'organizations_list':           organizations_list,
        'organization_name':            organization_name,
        'organization_twitter_handle':  organization_twitter_handle,
        'organization_facebook':        organization_facebook,
        'organization_website':         organization_website,
        'state_code':                   state_code,
        'state_list':                   sorted_state_list,
        'upcoming_election_list':       upcoming_election_list,
    }
    return render(request, 'voter_guide/voter_guide_search.html', template_values)
