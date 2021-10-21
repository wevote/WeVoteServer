# candidate/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import re
import string
from datetime import datetime
import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import BallotReturnedListManager
from bookmark.models import BookmarkItemList
from config.base import get_environment_variable
from election.controllers import retrieve_upcoming_election_id_list
from election.models import ElectionManager
from exception.models import handle_record_found_more_than_one_exception, \
    handle_record_not_found_exception, print_to_log
from google_custom_search.models import GoogleSearchUser, GoogleSearchUserManager
from import_export_batches.models import BatchManager
from import_export_twitter.controllers import refresh_twitter_candidate_details
from import_export_vote_smart.models import VoteSmartRatingOneCandidate
from import_export_vote_smart.votesmart_local import VotesmartApiError
from measure.models import ContestMeasure
from office.models import ContestOffice, ContestOfficeManager
from politician.models import PoliticianManager
from position.models import PositionEntered, PositionListManager
from twitter.models import TwitterLinkPossibility, TwitterUserManager
from voter.models import voter_has_authority
from voter_guide.models import VoterGuide
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, list_intersection, \
    positive_value_exists, STATE_CODE_MAP, display_full_name_with_correct_capitalization
from wevote_settings.models import RemoteRequestHistory, \
    RETRIEVE_POSSIBLE_GOOGLE_LINKS, RETRIEVE_POSSIBLE_TWITTER_HANDLES
from .controllers import candidates_import_from_master_server, candidates_import_from_sample_file, \
    candidate_politician_match, fetch_duplicate_candidate_count, figure_out_candidate_conflict_values, \
    find_duplicate_candidate, \
    merge_if_duplicate_candidates, merge_these_two_candidates, \
    retrieve_candidate_photos, \
    retrieve_candidate_politician_match_options, retrieve_next_or_most_recent_office_for_candidate, \
    save_image_to_candidate_table, \
    save_google_search_link_to_candidate_table
from .models import CandidateCampaign, CandidateListManager, CandidateManager, CandidateToOfficeLink, \
    CANDIDATE_UNIQUE_IDENTIFIERS, PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_UPLOADED, PROFILE_IMAGE_TYPE_VOTE_USA


CANDIDATES_SYNC_URL = get_environment_variable("CANDIDATES_SYNC_URL")  # candidatesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
def candidates_sync_out_view(request):  # candidatesSyncOut
    status = ''
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    candidate_search = request.GET.get('candidate_search', '')

    if not positive_value_exists(google_civic_election_id):
        json_data = {
            'success': False,
            'status': 'GOOGLE_CIVIC_ELECTION_ID_REQUIRED'
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    candidate_list_manager = CandidateListManager()
    google_civic_election_id_list = [google_civic_election_id]
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
        google_civic_election_id_list=google_civic_election_id_list,
        limit_to_this_state_code=state_code)
    candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    try:
        candidate_list = CandidateCampaign.objects.using('readonly').all()
        candidate_list = candidate_list.filter(we_vote_id__in=candidate_we_vote_id_list)
        filters = []
        if positive_value_exists(candidate_search):
            new_filter = Q(candidate_name__icontains=candidate_search)
            filters.append(new_filter)

            new_filter = Q(candidate_twitter_handle__icontains=candidate_search)
            filters.append(new_filter)

            new_filter = Q(candidate_url__icontains=candidate_search)
            filters.append(new_filter)

            new_filter = Q(candidate_contact_form_url__icontains=candidate_search)
            filters.append(new_filter)

            new_filter = Q(party__icontains=candidate_search)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=candidate_search)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                candidate_list = candidate_list.filter(final_filters)

        candidate_list_dict = candidate_list.values(
            'ballot_guide_official_statement',
            'ballotpedia_candidate_id',
            'ballotpedia_candidate_name',
            'ballotpedia_candidate_url',
            'ballotpedia_candidate_summary',
            'ballotpedia_election_id',
            'ballotpedia_image_id',
            'ballotpedia_office_id',
            'ballotpedia_page_title',
            'ballotpedia_person_id',
            'ballotpedia_photo_url',
            'ballotpedia_profile_image_url_https',
            'ballotpedia_race_id',
            'birth_day_text',
            'candidate_contact_form_url',
            'candidate_email',
            'candidate_gender',
            'candidate_instagram_url',
            'candidate_is_incumbent',
            'candidate_is_top_ticket',
            'candidate_name',
            'candidate_participation_status',
            'candidate_phone',
            'candidate_twitter_handle',
            'candidate_ultimate_election_date',
            'candidate_url',
            'candidate_year',
            'contest_office_name',
            'contest_office_we_vote_id',
            'crowdpac_candidate_id',
            'ctcl_uuid',
            'do_not_display_on_ballot',
            'facebook_profile_image_url_https',
            'facebook_url',
            'facebook_url_is_broken',
            'google_civic_candidate_name',
            'google_civic_candidate_name2',
            'google_civic_candidate_name3',
            'google_civic_election_id',
            'google_plus_url',
            'linkedin_url',
            'linkedin_photo_url',
            'maplight_id',
            'ocd_division_id',
            'order_on_ballot',
            'other_source_url',
            'other_source_photo_url',
            'party',
            'photo_url',
            'photo_url_from_ctcl',
            'photo_url_from_maplight',
            'photo_url_from_vote_smart',
            'photo_url_from_vote_usa',
            'politician_we_vote_id',
            'profile_image_type_currently_active',
            'state_code',
            'twitter_description',
            'twitter_followers_count',
            'twitter_location',
            'twitter_name',
            'twitter_profile_background_image_url_https',
            'twitter_profile_banner_url_https',
            'twitter_profile_image_url_https',
            'twitter_url',
            'twitter_user_id',
            'vote_smart_id',
            'vote_usa_office_id',
            'vote_usa_politician_id',
            'vote_usa_profile_image_url_https',
            'we_vote_hosted_profile_facebook_image_url_large',
            'we_vote_hosted_profile_facebook_image_url_medium',
            'we_vote_hosted_profile_facebook_image_url_tiny',
            'we_vote_hosted_profile_image_url_large',
            'we_vote_hosted_profile_image_url_medium',
            'we_vote_hosted_profile_image_url_tiny',
            'we_vote_hosted_profile_twitter_image_url_large',
            'we_vote_hosted_profile_twitter_image_url_medium',
            'we_vote_hosted_profile_twitter_image_url_tiny',
            'we_vote_hosted_profile_uploaded_image_url_large',
            'we_vote_hosted_profile_uploaded_image_url_medium',
            'we_vote_hosted_profile_uploaded_image_url_tiny',
            'we_vote_hosted_profile_vote_usa_image_url_large',
            'we_vote_hosted_profile_vote_usa_image_url_medium',
            'we_vote_hosted_profile_vote_usa_image_url_tiny',
            'we_vote_id',
            'wikipedia_page_id',
            'wikipedia_page_title',
            'wikipedia_photo_url',
            'withdrawal_date',
            'withdrawn_from_election',
            'youtube_url',
            )
        if candidate_list_dict:
            candidate_list_json = list(candidate_list_dict)
            return HttpResponse(json.dumps(candidate_list_json), content_type='application/json')
    except Exception as e:
        status += "CANDIDATE_LIST_MISSING: " + str(e) + " "

    json_data = {
        'success': False,
        'status': status
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


# This page does not need to be protected.
def candidate_to_office_link_sync_out_view(request):  # candidateToOfficeLinkSyncOut
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    try:
        query = CandidateToOfficeLink.objects.using('readonly').all()
        if positive_value_exists(google_civic_election_id):
            query = query.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            query = query.filter(state_code__iexact=state_code)
        # get the data using values_list
        candidate_to_office_link_dict = query.values(
            'candidate_we_vote_id', 'contest_office_we_vote_id',
            'google_civic_election_id', 'state_code')
        if candidate_to_office_link_dict:
            candidate_to_office_link_json = list(candidate_to_office_link_dict)
            return HttpResponse(json.dumps(candidate_to_office_link_json), content_type='application/json')
    except CandidateToOfficeLink.DoesNotExist:
        pass

    json_data = {
        'success': False,
        'status': 'CANDIDATE_TO_OFFICES_LINK_SYNC_OUT_VIEW-LIST_MISSING '
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def candidates_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in CANDIDATES_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = candidates_import_from_master_server(request, google_civic_election_id, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Candidates import completed. '
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
def candidates_import_from_sample_file_view(request):
    """
    This gives us sample organizations, candidates, and positions for testing
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # We are importing candidate data (and not politician data) because all we are doing is making sure we
    #  sync to the same We Vote ID. This is critical so we can link Positions to Organization & CandidateCampaign.
    # At this point (June 2015) we assume the politicians have been imported from Google Civic. We aren't assigning
    # the politicians a We Vote id, but instead use their full name as the identifier
    candidates_import_from_sample_file(request, False)

    messages.add_message(request, messages.INFO, 'Candidates imported.')

    return HttpResponseRedirect(reverse('import_export:import_export_index', args=()))


@login_required
def candidate_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    hide_pagination = False

    candidate_search = request.GET.get('candidate_search', '')
    current_page_url = request.get_full_path()
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = positive_value_exists(request.GET.get('hide_candidate_tools', 0))
    hide_candidates_with_photos = \
        positive_value_exists(request.GET.get('hide_candidates_with_photos', False))
    migrate_to_candidate_link = positive_value_exists(request.GET.get('migrate_to_candidate_link', False))
    page = convert_to_int(request.GET.get('page', 0))
    page = page if positive_value_exists(page) else 0  # Prevent negative pages
    show_all = positive_value_exists(request.GET.get('show_all', False))
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    show_candidates_without_twitter = positive_value_exists(request.GET.get('show_candidates_without_twitter', False))
    show_candidates_with_best_twitter_options = \
        positive_value_exists(request.GET.get('show_candidates_with_best_twitter_options', False))
    show_candidates_with_twitter_options = \
        positive_value_exists(request.GET.get('show_candidates_with_twitter_options', False))
    show_election_statistics = positive_value_exists(request.GET.get('show_election_statistics', False))
    show_marquee_or_battleground = positive_value_exists(request.GET.get('show_marquee_or_battleground', False))

    review_mode = positive_value_exists(request.GET.get('review_mode', False))

    # # Remove "&page=" and everything after
    # if "&page=" in current_page_url:
    #     location_of_page_variable = current_page_url.find("&page=")
    #     if location_of_page_variable != -1:
    #         current_page_url = current_page_url[:location_of_page_variable]
    # Remove "&page="
    if "&page=" in current_page_url:
        # This will leave harmless number in URL
        current_page_url = current_page_url.replace("&page=", "&")
    # Remove "&hide_candidate_tools=1"
    if current_page_url:
        current_page_minus_candidate_tools_url = current_page_url.replace("&hide_candidate_tools=1", "")
        current_page_minus_candidate_tools_url = current_page_minus_candidate_tools_url.replace(
            "&hide_candidate_tools=0", "")
    else:
        current_page_minus_candidate_tools_url = current_page_url
    previous_page = page - 1
    previous_page_url = current_page_url + "&page=" + str(previous_page)
    next_page = page + 1
    next_page_url = current_page_url + "&page=" + str(next_page)
    state_code = request.GET.get('state_code', '')
    state_list = STATE_CODE_MAP
    state_list_modified = {}
    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()

    if positive_value_exists(google_civic_election_id) or positive_value_exists(migrate_to_candidate_link):
        candidate_query = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id):
            candidate_query = candidate_query.filter(google_civic_election_id=google_civic_election_id)
        candidate_query = candidate_query.filter(migrated_to_link=False)
        candidate_list = list(candidate_query)
        candidates_migrated = 0
        for one_candidate in candidate_list:
            if positive_value_exists(one_candidate.we_vote_id) \
                    and positive_value_exists(one_candidate.contest_office_we_vote_id) \
                    and positive_value_exists(one_candidate.google_civic_election_id):
                results = candidate_manager.get_or_create_candidate_to_office_link(
                    candidate_we_vote_id=one_candidate.we_vote_id,
                    contest_office_we_vote_id=one_candidate.contest_office_we_vote_id,
                    google_civic_election_id=convert_to_int(one_candidate.google_civic_election_id),
                    state_code=one_candidate.state_code)
                if not positive_value_exists(results['success']):
                    # Break out of loop
                    messages.add_message(request, messages.ERROR, "Could not migrate: " + str(results['status']))
                else:
                    if positive_value_exists(results['new_candidate_to_office_link_created']):
                        pass
                    one_candidate.migrated_to_link = True
                    one_candidate.save()
                    candidates_migrated += 1
        if positive_value_exists(candidates_migrated) or positive_value_exists(migrate_to_candidate_link):
            messages.add_message(request, messages.INFO, "candidates_migrated: " + str(candidates_migrated))

    google_civic_election_id_list_generated = False
    if positive_value_exists(google_civic_election_id):
        google_civic_election_id_list = [convert_to_int(google_civic_election_id)]
        google_civic_election_id_list_generated = True
    elif positive_value_exists(show_all_elections):
        google_civic_election_id_list = []
    else:
        # Limit to just upcoming elections
        google_civic_election_id_list_generated = True
        google_civic_election_id_list = retrieve_upcoming_election_id_list()

    candidate_we_vote_id_list = []
    if google_civic_election_id_list_generated:
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list,
            limit_to_this_state_code=state_code)
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    for one_state_code, one_state_name in state_list.items():
        count_result = candidate_list_manager.retrieve_candidate_count_for_election_and_state(
            google_civic_election_id_list, one_state_code)
        state_name_modified = one_state_name
        if positive_value_exists(count_result['candidate_count']):
            state_name_modified += " - " + str(count_result['candidate_count'])
            state_list_modified[one_state_code] = state_name_modified
        elif str(one_state_code.lower()) == str(state_code.lower()):
            state_name_modified += " - 0"
            state_list_modified[one_state_code] = state_name_modified
        else:
            # Do not include state in drop-down if there aren't any candidates in that state
            pass
    sorted_state_list = sorted(state_list_modified.items())
    # if positive_value_exists(google_civic_election_id):
    #     pass
    # else:
    #     sorted_state_list = sorted(state_list.items())

    if positive_value_exists(review_mode):
        if positive_value_exists(google_civic_election_id):
            # Only show all if there is an election id
            show_all = True
        else:
            messages.add_message(request, messages.ERROR, "Please choose election id.")

    candidate_list = []
    candidate_list_count = 0
    candidate_count_start = 0

    election_manager = ElectionManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    battleground_office_we_vote_ids = []
    battleground_candidate_we_vote_id_list = []
    if positive_value_exists(show_marquee_or_battleground):
        # If we are trying to highlight all of the candidates that are in battleground races,
        # collect the office_we_vote_id's
        try:
            office_queryset = ContestOffice.objects.all()
            if positive_value_exists(google_civic_election_id):
                office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
            elif positive_value_exists(show_all_elections):
                # Return offices from all elections
                pass
            else:
                office_queryset = office_queryset.filter(google_civic_election_id__in=google_civic_election_id_list)
            if positive_value_exists(state_code):
                office_queryset = office_queryset.filter(state_code__iexact=state_code)
            if positive_value_exists(show_marquee_or_battleground):
                office_queryset = office_queryset.filter(Q(ballotpedia_is_marquee=True) | Q(is_battleground_race=True))
            office_queryset = office_queryset.order_by("office_name")
            office_list_count = office_queryset.count()
            office_list = list(office_queryset)

            if len(office_list):
                battleground_office_we_vote_ids = []
                for one_office in office_list:
                    battleground_office_we_vote_ids.append(one_office.we_vote_id)

            if len(battleground_office_we_vote_ids) > 0:
                results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_office_list(
                    contest_office_we_vote_id_list=battleground_office_we_vote_ids,
                    limit_to_this_state_code=state_code)
                battleground_candidate_we_vote_id_list = results['candidate_we_vote_id_list']
            else:
                battleground_candidate_we_vote_id_list = []

        except ContestOffice.DoesNotExist:
            # No offices found. Not a problem.
            office_list_count = 0
        except Exception as e:
            office_list_count = 0

    # Figure out the subset of candidate_we_vote_ids to look up
    filtered_candidate_we_vote_id_list = []
    if google_civic_election_id_list_generated and show_marquee_or_battleground:
        filtered_candidate_we_vote_id_list = list_intersection(
            candidate_we_vote_id_list, battleground_candidate_we_vote_id_list)
    elif google_civic_election_id_list_generated:
        filtered_candidate_we_vote_id_list = candidate_we_vote_id_list
    elif show_marquee_or_battleground:
        filtered_candidate_we_vote_id_list = battleground_candidate_we_vote_id_list
    try:
        candidate_query = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id_list_generated) \
                or positive_value_exists(show_marquee_or_battleground):
            candidate_query = candidate_query.filter(we_vote_id__in=filtered_candidate_we_vote_id_list)
        if positive_value_exists(state_code):
            candidate_query = candidate_query.filter(state_code__iexact=state_code)
        if positive_value_exists(candidate_search):
            search_words = candidate_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(ballotpedia_candidate_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_candidate_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_candidate_summary__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_office_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_person_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_race_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(candidate_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(candidate_twitter_handle__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(candidate_url__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(candidate_contact_form_url__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(contest_office_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(google_civic_candidate_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(google_civic_candidate_name2__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(google_civic_candidate_name3__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(party__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(twitter_description__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(vote_usa_office_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(vote_usa_politician_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    candidate_query = candidate_query.filter(final_filters)
        if positive_value_exists(hide_candidates_with_photos):
            # Show candidates that do NOT have photos
            candidate_query = candidate_query.filter(
                Q(we_vote_hosted_profile_image_url_medium__isnull=True) | Q(we_vote_hosted_profile_image_url_medium=""))
        if positive_value_exists(show_candidates_with_best_twitter_options):
            # Show candidates with TwitterLinkPossibilities of greater than 60
            candidate_query = candidate_query.filter(
                Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle=""))
            try:
                twitter_query = TwitterLinkPossibility.objects.filter(likelihood_score__gte=60, not_a_match=False)
                twitter_list = twitter_query.values_list('candidate_campaign_we_vote_id', flat=True).distinct()
                if len(twitter_list):
                    candidate_query = candidate_query.filter(we_vote_id__in=twitter_list)
            except Exception as e:
                pass
        elif positive_value_exists(show_candidates_with_twitter_options):
            # Show candidates that we have Twitter search results for
            try:
                candidate_query = candidate_query.filter(
                    Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle=""))

                twitter_query = TwitterLinkPossibility.objects.filter(not_a_match=False)
                twitter_possibility_list = twitter_query.values_list('candidate_campaign_we_vote_id', flat=True) \
                    .distinct()
                if len(twitter_possibility_list):
                    candidate_query = candidate_query.filter(we_vote_id__in=twitter_possibility_list)
            except Exception as e:
                pass
        elif positive_value_exists(show_candidates_without_twitter):
            # Don't show candidates that already have Twitter handles
            candidate_query = candidate_query.filter(
                Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle=""))

        candidate_query = candidate_query.order_by('candidate_name')
        candidate_list_count = candidate_query.count()

        candidate_count_start = 0
        if positive_value_exists(show_all):
            pass
        else:
            number_to_show_per_page = 10
            if candidate_list_count <= number_to_show_per_page:
                # Ignore pagination
                candidate_list = list(candidate_query)
                hide_pagination = True
            else:
                candidate_count_start = number_to_show_per_page * page
                candidate_count_end = candidate_count_start + number_to_show_per_page
                candidate_list = candidate_query[candidate_count_start:candidate_count_end]
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    # How many facebook_url's don't have facebook_profile_image_url_https
    # SELECT * FROM public.candidate_candidatecampaign where google_civic_election_id = '1000052' and facebook_url
    #     is not null and facebook_profile_image_url_https is null
    facebook_urls_without_picture_urls = 0
    if positive_value_exists(google_civic_election_id):
        try:
            candidate_facebook_missing_query = CandidateCampaign.objects.all()
            if positive_value_exists(google_civic_election_id):
                candidate_facebook_missing_query = \
                    candidate_facebook_missing_query.filter(we_vote_id__in=candidate_we_vote_id_list)

            # include profile images that are null or ''
            candidate_facebook_missing_query = candidate_facebook_missing_query. \
                filter(Q(facebook_profile_image_url_https__isnull=True) | Q(facebook_profile_image_url_https__exact=''))

            # exclude facebook_urls that are null or ''
            candidate_facebook_missing_query = candidate_facebook_missing_query.exclude(facebook_url__isnull=True). \
                exclude(facebook_url__iexact='').exclude(facebook_url_is_broken='True')

            facebook_urls_without_picture_urls = candidate_facebook_missing_query.count()

        except Exception as e:
            logger.error("Find facebook URLs without facebook pictures in candidate: ", e)

    status_print_list = ""
    status_print_list += "candidate_list_count: " + str(candidate_list_count) + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    # Provide this election to the template so we can show election statistics
    election = None
    if positive_value_exists(google_civic_election_id):
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            ballot_returned_list_manager = BallotReturnedListManager()
            batch_manager = BatchManager()
            timezone = pytz.timezone("America/Los_Angeles")
            datetime_now = timezone.localize(datetime.now())
            if positive_value_exists(election.election_day_text):
                date_of_election = timezone.localize(datetime.strptime(election.election_day_text, "%Y-%m-%d"))
                if date_of_election > datetime_now:
                    time_until_election = date_of_election - datetime_now
                    election.days_until_election = convert_to_int("%d" % time_until_election.days)

            # How many offices?
            office_list_query = ContestOffice.objects.all()
            office_list_query = office_list_query.filter(google_civic_election_id=election.google_civic_election_id)
            election.office_count = office_list_query.count()

            if positive_value_exists(show_election_statistics):
                office_list = list(office_list_query)

                election.ballot_returned_count = \
                    ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                        election.google_civic_election_id, election.state_code)
                election.ballot_location_display_option_on_count = \
                    ballot_returned_list_manager.fetch_ballot_location_display_option_on_count_for_election(
                        election.google_civic_election_id, election.state_code)
                if election.ballot_returned_count < 500:
                    batch_set_source = "IMPORT_BALLOTPEDIA_BALLOT_ITEMS"
                    results = batch_manager.retrieve_unprocessed_batch_set_info_by_election_and_set_source(
                        election.google_civic_election_id, batch_set_source)
                    if positive_value_exists(results['batches_not_processed']):
                        election.batches_not_processed = results['batches_not_processed']
                        election.batches_not_processed_batch_set_id = results['batch_set_id']

                # How many offices with zero candidates?
                offices_with_candidates_count = 0
                offices_without_candidates_count = 0
                for one_office in office_list:
                    candidate_list_query = CandidateCampaign.objects.all()
                    candidate_list_query = candidate_list_query.filter(contest_office_id=one_office.id)
                    candidate_count = candidate_list_query.count()
                    if positive_value_exists(candidate_count):
                        offices_with_candidates_count += 1
                    else:
                        offices_without_candidates_count += 1
                election.offices_with_candidates_count = offices_with_candidates_count
                election.offices_without_candidates_count = offices_without_candidates_count

                # if positive_value_exists(google_civic_election_id_list_generated) \
                #         or positive_value_exists(show_marquee_or_battleground):
                #     candidate_query = candidate_query.filter(we_vote_id__in=filtered_candidate_we_vote_id_list)
                # How many candidates?
                candidate_list_query = CandidateCampaign.objects.all()
                candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
                election.candidate_count = candidate_list_query.count()

                # How many without photos?
                candidate_list_query = CandidateCampaign.objects.all()
                candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
                candidate_list_query = candidate_list_query.filter(
                    Q(we_vote_hosted_profile_image_url_tiny__isnull=True) | Q(we_vote_hosted_profile_image_url_tiny='')
                )
                election.candidates_without_photo_count = candidate_list_query.count()
                if positive_value_exists(election.candidate_count):
                    election.candidates_without_photo_percentage = \
                        100 * (election.candidates_without_photo_count / election.candidate_count)

                # How many measures?
                measure_list_query = ContestMeasure.objects.all()
                measure_list_query = measure_list_query.filter(
                    google_civic_election_id=election.google_civic_election_id)
                election.measure_count = measure_list_query.count()

                # Number of Voter Guides
                voter_guide_query = VoterGuide.objects.filter(
                    google_civic_election_id=election.google_civic_election_id)
                voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
                election.voter_guides_count = voter_guide_query.count()

                # Number of Public Positions
                position_query = PositionEntered.objects.all()
                # Catch both candidates and measures (which have google_civic_election_id in the Positions table)
                position_query = position_query.filter(
                    Q(google_civic_election_id=election.google_civic_election_id) |
                    Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
                # As of Aug 2018 we are no longer using PERCENT_RATING
                position_query = position_query.exclude(stance__iexact='PERCENT_RATING')
                election.public_positions_count = position_query.count()

    # Attach the latest contest_office information
    modified_candidate_list = []
    for candidate in candidate_list:
        election_id_found_from_link = False
        office_results = \
            retrieve_next_or_most_recent_office_for_candidate(candidate_we_vote_id=candidate.we_vote_id)
        if positive_value_exists(office_results['google_civic_election_id']):
            candidate.google_civic_election_id = office_results['google_civic_election_id']
            election_id_found_from_link = True
        if office_results['contest_office_found']:
            contest_office = office_results['contest_office']
            candidate.contest_office_we_vote_id = contest_office.we_vote_id
            candidate.contest_office_name = contest_office.office_name
            if not election_id_found_from_link:
                candidate.google_civic_election_id = contest_office.google_civic_election_id
        modified_candidate_list.append(candidate)
    candidate_list = modified_candidate_list

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

    total_twitter_handles = 0
    if positive_value_exists(review_mode):
        # Attach the positions_count, if any, to each candidate in list
        position_list_manager = PositionListManager()
        for candidate in candidate_list:
            candidate.positions_count = position_list_manager.fetch_public_positions_count_for_candidate(
                candidate.id, candidate.we_vote_id)
            if positive_value_exists(candidate.candidate_twitter_handle):
                total_twitter_handles += 1
    elif positive_value_exists(show_candidates_with_best_twitter_options) \
            or positive_value_exists(show_candidates_with_twitter_options):
        # Attach the best guess Twitter account, if any, to each candidate in list
        for candidate in candidate_list:
            try:
                twitter_possibility_query = TwitterLinkPossibility.objects.order_by('-likelihood_score')
                twitter_possibility_query = twitter_possibility_query.filter(
                    candidate_campaign_we_vote_id=candidate.we_vote_id,
                    not_a_match=False)
                twitter_possibility_list = list(twitter_possibility_query)
                candidate.twitter_possibility_list_count = len(twitter_possibility_list)
                if twitter_possibility_list and positive_value_exists(len(twitter_possibility_list)):
                    candidate.candidate_merge_possibility = twitter_possibility_list[0]
                else:
                    request_history_query = RemoteRequestHistory.objects.filter(
                        candidate_campaign_we_vote_id__iexact=candidate.we_vote_id,
                        kind_of_action=RETRIEVE_POSSIBLE_TWITTER_HANDLES)
                    request_history_list = list(request_history_query)
                    if request_history_list and positive_value_exists(len(request_history_list)):
                        candidate.no_twitter_possibilities_found = True
            except Exception as e:
                candidate.candidate_merge_possibility = None

        # Attach the best guess google search, if any, to each candidate in list
        for candidate in candidate_list:
            try:
                google_search_possibility_query = GoogleSearchUser.objects.filter(
                    candidate_campaign_we_vote_id=candidate.we_vote_id). \
                    exclude(item_image__isnull=True).exclude(item_image__exact='')
                google_search_possibility_query = google_search_possibility_query.order_by(
                    '-chosen_and_updated', 'not_a_match', '-likelihood_score')
                google_search_merge_possibility = list(google_search_possibility_query)
                if google_search_merge_possibility and positive_value_exists(len(google_search_merge_possibility)):
                    candidate.google_search_merge_possibility = google_search_possibility_query[0]
                else:
                    request_history_query = RemoteRequestHistory.objects.filter(
                        candidate_campaign_we_vote_id__iexact=candidate.we_vote_id,
                        kind_of_action=RETRIEVE_POSSIBLE_GOOGLE_LINKS)
                    request_history_list = list(request_history_query)
                    if request_history_list and positive_value_exists(len(request_history_list)):
                        candidate.no_google_possibilities_found = True
            except Exception as e:
                candidate.google_search_merge_possibility = None

    template_values = {
        'candidate_count_start':    candidate_count_start,
        'candidate_list':           candidate_list,
        'candidate_search':         candidate_search,
        'current_page_number':      page,
        'current_page_minus_candidate_tools_url':   current_page_minus_candidate_tools_url,
        'election':                 election,
        'election_list':            election_list,
        'facebook_urls_without_picture_urls':       facebook_urls_without_picture_urls,
        'google_civic_election_id': google_civic_election_id,
        'hide_candidate_tools':     hide_candidate_tools,
        'hide_candidates_with_photos':  hide_candidates_with_photos,
        'hide_pagination':          hide_pagination,
        'messages_on_stage':        messages_on_stage,
        'next_page_url':            next_page_url,
        'previous_page_url':        previous_page_url,
        'review_mode':              review_mode,
        'show_all_elections':       show_all_elections,
        'show_candidates_with_best_twitter_options':    show_candidates_with_best_twitter_options,
        'show_candidates_with_twitter_options': show_candidates_with_twitter_options,
        'show_candidates_without_twitter': show_candidates_without_twitter,
        'show_election_statistics': show_election_statistics,
        'show_marquee_or_battleground': show_marquee_or_battleground,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
        'total_twitter_handles':    total_twitter_handles,
    }
    return render(request, 'candidate/candidate_list.html', template_values)


@login_required
def candidate_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    contest_office_id = request.GET.get('contest_office_id', 0)
    state_code = request.GET.get('state_code', "")

    if not positive_value_exists(contest_office_id):
        # If election id is missing, ...
        url_variables = "?google_civic_election_id=" + google_civic_election_id + "&state_code=" + state_code
        messages.add_message(request, messages.ERROR, 'To create a new candidate, please add from an existing office.')
        return HttpResponseRedirect(reverse('office:office_list', args=()) + url_variables)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    candidate_name = request.GET.get('candidate_name', "")
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', "")
    candidate_twitter_handle = request.GET.get('candidate_twitter_handle', "")
    candidate_url = request.GET.get('candidate_url', "")
    candidate_contact_form_url = request.GET.get('candidate_contact_form_url', "")
    party = request.GET.get('party', "")
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', "")
    vote_smart_id = request.GET.get('vote_smart_id', "")
    maplight_id = request.GET.get('maplight_id', "")
    page = request.GET.get('page', 0)
    politician_we_vote_id = request.GET.get('politician_we_vote_id', "")

    office_manager = ContestOfficeManager()
    candidate_list_manager = CandidateListManager()

    # These are the Offices already entered for this election
    try:
        office_queryset = ContestOffice.objects.order_by('office_name')
        office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
        contest_office_list = list(office_queryset)

    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        contest_office_list = []

    # No try/except because we want it to fail if query fails
    candidate_query = CandidateCampaign.objects.all()
    results = office_manager.retrieve_contest_office_from_id(contest_office_id)
    if not positive_value_exists(results['contest_office_found']):
        url_variables = "?google_civic_election_id=" + google_civic_election_id + "&state_code=" + state_code
        messages.add_message(request, messages.ERROR,
                             'Office could not be found in database.')
        return HttpResponseRedirect(reverse('office:office_list', args=()) + url_variables)

    office = results['contest_office']
    office_name = office.office_name
    office_we_vote_id = office.we_vote_id
    state_code_from_office = office.state_code

    # Its helpful to see existing candidates when entering a new candidate
    candidate_we_vote_id_list = candidate_list_manager.fetch_candidate_we_vote_id_list_from_office_we_vote_id(
        office_we_vote_id=office_we_vote_id)
    candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
    candidate_list = candidate_query.order_by('candidate_name')[:500]

    election_manager = ElectionManager()
    election_results = election_manager.retrieve_election(google_civic_election_id)
    state_code_from_election = ""
    if election_results['election_found']:
        election = election_results['election']
        election_found = election_results['election_found']
        state_code_from_election = election.get_election_state()

    best_state_code = ''
    if positive_value_exists(state_code_from_office):
        best_state_code = state_code_from_office
    elif positive_value_exists(state_code):
        best_state_code = state_code
    elif positive_value_exists(state_code_from_election):
        best_state_code = state_code_from_election

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
        'state_code':                       best_state_code,
        'candidate_twitter_handle':         candidate_twitter_handle,
        'candidate_url':                    candidate_url,
        'candidate_contact_form_url':       candidate_contact_form_url,
        'party':                            party,
        'ballot_guide_official_statement':  ballot_guide_official_statement,
        'vote_smart_id':                    vote_smart_id,
        'maplight_id':                      maplight_id,
        'office_name':                      office_name,
        'page':                             page,
        'politician_we_vote_id':            politician_we_vote_id,
    }
    return render(request, 'candidate/candidate_edit.html', template_values)


@login_required
def candidate_edit_view(request, candidate_id=0, candidate_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    candidate_name = request.GET.get('candidate_name', False)
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', False)
    google_civic_candidate_name2 = request.GET.get('google_civic_candidate_name2', False)
    google_civic_candidate_name3 = request.GET.get('google_civic_candidate_name3', False)
    candidate_twitter_handle = request.GET.get('candidate_twitter_handle', False)
    candidate_url = request.GET.get('candidate_url', False)
    candidate_contact_form_url = request.GET.get('candidate_contact_form_url', False)
    facebook_url = request.GET.get('facebook_url', False)
    candidate_email = request.GET.get('candidate_email', False)
    candidate_phone = request.GET.get('candidate_phone', False)
    party = request.GET.get('party', False)
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', False)
    ballotpedia_candidate_id = request.GET.get('ballotpedia_candidate_id', False)
    ballotpedia_candidate_name = request.GET.get('ballotpedia_candidate_name', False)
    ballotpedia_candidate_url = request.GET.get('ballotpedia_candidate_url', False)
    ballotpedia_office_id = request.GET.get('ballotpedia_office_id', False)
    ballotpedia_person_id = request.GET.get('ballotpedia_person_id', False)
    ballotpedia_race_id = request.GET.get('ballotpedia_race_id', False)
    vote_smart_id = request.GET.get('vote_smart_id', False)
    maplight_id = request.GET.get('maplight_id', False)
    page = request.GET.get('page', 0)
    state_code = request.GET.get('state_code', "")
    show_all_google_search_users = request.GET.get('show_all_google_search_users', False)
    show_all_twitter_search_results = request.GET.get('show_all_twitter_search_results', False)
    withdrawal_date = request.GET.get('withdrawal_date', False)
    withdrawn_from_election = positive_value_exists(request.GET.get('withdrawn_from_election', False))
    do_not_display_on_ballot = positive_value_exists(request.GET.get('do_not_display_on_ballot', False))

    messages_on_stage = get_messages(request)
    candidate_id = convert_to_int(candidate_id)
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    candidate_list_manager = CandidateListManager()
    google_civic_election_id = 0

    try:
        if positive_value_exists(candidate_id):
            candidate_on_stage = CandidateCampaign.objects.get(id=candidate_id)
        else:
            candidate_on_stage = CandidateCampaign.objects.get(we_vote_id=candidate_we_vote_id)
        candidate_on_stage_found = True
        candidate_id = candidate_on_stage.id
        candidate_we_vote_id = candidate_on_stage.we_vote_id
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
            candidate_position_query = PositionEntered.objects.order_by('stance')
            # As of Aug 2018 we are no longer using PERCENT_RATING
            candidate_position_query = candidate_position_query.exclude(stance__iexact='PERCENT_RATING')
            candidate_position_query = candidate_position_query.filter(candidate_campaign_id=candidate_id)
            candidate_position_list = list(candidate_position_query)
            # if positive_value_exists(google_civic_election_id):
            #     organization_position_list = candidate_position_list.filter(
            #         google_civic_election_id=google_civic_election_id)
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            candidate_position_list = []

        # Working with Offices for this election
        # try:
        #     office_list_query = ContestOffice.objects.order_by('office_name')
        #     office_list_query = office_list_query.filter(
        #         google_civic_election_id=candidate_on_stage.google_civic_election_id)
        #     contest_office_list = list(office_list_query)
        # except Exception as e:
        #     handle_record_not_found_exception(e, logger=logger)
        #     contest_office_list = []

        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            candidate_we_vote_id_list=[candidate_we_vote_id])
        candidate_to_office_link_list = results['candidate_to_office_link_list']

        # Was a candidate_merge_possibility_found?
        candidate_on_stage.candidate_merge_possibility_found = True  # TODO DALE Make dynamic

        twitter_link_possibility_list = []
        try:
            twitter_possibility_query = TwitterLinkPossibility.objects.order_by('not_a_match', '-likelihood_score')
            twitter_possibility_query = twitter_possibility_query.filter(
                candidate_campaign_we_vote_id=candidate_on_stage.we_vote_id)
            if positive_value_exists(show_all_twitter_search_results):
                twitter_link_possibility_list = list(twitter_possibility_query)
            else:
                twitter_link_possibility_list.append(twitter_possibility_query[0])
        except Exception as e:
            pass

        google_search_possibility_list = []
        google_search_possibility_total_count = 0
        try:
            google_search_possibility_query = GoogleSearchUser.objects.filter(
                candidate_campaign_we_vote_id=candidate_on_stage.we_vote_id)
            google_search_possibility_query = google_search_possibility_query.order_by(
                '-chosen_and_updated', 'not_a_match', '-likelihood_score')
            google_search_possibility_total_count = google_search_possibility_query.count()
            if positive_value_exists(show_all_google_search_users):
                google_search_possibility_list = list(google_search_possibility_query)
            else:
                google_search_possibility_list = google_search_possibility_query[:1]
        except Exception as e:
            pass

        if positive_value_exists(candidate_on_stage.candidate_name):
            raw = candidate_on_stage.candidate_name
            cnt = sum(1 for c in raw if c.isupper())
            if cnt > 5:
                humanized = display_full_name_with_correct_capitalization(raw)
                humanized_cleaned = humanized.replace('(', '').replace(')', '')
                candidate_on_stage.candidate_name_normalized = string.capwords(humanized_cleaned)

        template_values = {
            'messages_on_stage':                messages_on_stage,
            'candidate':                        candidate_on_stage,
            'rating_list':                      rating_list,
            'candidate_position_list':          candidate_position_list,
            'candidate_to_office_link_list':    candidate_to_office_link_list,
            # 'office_list':                      contest_office_list,
            # 'contest_office_we_vote_id':        contest_office_we_vote_id,
            # 'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'twitter_link_possibility_list':    twitter_link_possibility_list,
            'google_search_possibility_list':   google_search_possibility_list,
            'google_search_possibility_total_count':    google_search_possibility_total_count,
            # Incoming variables, not saved yet
            'candidate_name':                   candidate_name,
            'google_civic_candidate_name':      google_civic_candidate_name,
            'google_civic_candidate_name2':     google_civic_candidate_name2,
            'google_civic_candidate_name3':     google_civic_candidate_name3,
            'candidate_twitter_handle':         candidate_twitter_handle,
            'candidate_url':                    candidate_url,
            'candidate_contact_form_url':       candidate_contact_form_url,
            'facebook_url':                     facebook_url,
            'candidate_email':                  candidate_email,
            'candidate_phone':                  candidate_phone,
            'party':                            party,
            'ballot_guide_official_statement':  ballot_guide_official_statement,
            'ballotpedia_candidate_id':         ballotpedia_candidate_id,
            'ballotpedia_candidate_name':       ballotpedia_candidate_name,
            'ballotpedia_candidate_url':        ballotpedia_candidate_url,
            'ballotpedia_office_id':            ballotpedia_office_id,
            'ballotpedia_person_id':            ballotpedia_person_id,
            'ballotpedia_race_id':              ballotpedia_race_id,
            'vote_smart_id':                    vote_smart_id,
            'maplight_id':                      maplight_id,
            'page':                             page,
            # 'vote_usa_profile_image_url_https': vote_usa_profile_image_url_https,
            'withdrawal_date':                  withdrawal_date,
            'withdrawn_from_election':          withdrawn_from_election,
            'do_not_display_on_ballot':         do_not_display_on_ballot,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            # Incoming variables
            'vote_smart_id':        vote_smart_id,
        }
    return render(request, 'candidate/candidate_edit.html', template_values)


@login_required
def repair_imported_names_view(request):
    """
    Process repair imported names form
    http://localhost:8000/c/repair_imported_names/?is_candidate=true&start=0&count=25
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    is_candidate = positive_value_exists(request.GET.get('is_candidate', True))
    start = int(request.GET.get('start', 0))
    count = int(request.GET.get('count', 15))
    if is_candidate:
        candidate_list_manager = CandidateListManager()
        list_of_people_from_db, number_of_rows = candidate_list_manager.retrieve_candidates_with_misformatted_names(
            start, count)
    else:
        politician_manager = PoliticianManager()
        list_of_people_from_db, number_of_rows = politician_manager.retrieve_politicians_with_misformatted_names(
            start, count)

    people_list = []
    for person in list_of_people_from_db:
        name = person.candidate_name if is_candidate else person.politician_name
        highlight = False
        highlight = True if name.count('.') > 2 else highlight
        cap = re.search(r'\s([a-zA-Z]){2}\s|^([a-zA-Z]){2}\s|\s([a-zA-Z]){2}$(?<!JR|SR|MR)', name)
        highlight = True if cap is not None else highlight
        highlight = True if name[0] in string.punctuation else highlight
        highlight = True if name[-1] in string.punctuation else highlight
        short_office_name = ''
        if is_candidate:
            short_office_name = person.contest_office_name[0:30] \
                if (person.contest_office_name != "N" and person.contest_office_name is not None) else ''
        party = person.party.replace('Party Preference:', '') if person.party else ''

        person_item = {
            'person_name':                  name,
            'person_name_normalized':       person.person_name_normalized,
            'google_civic_candidate_name':  person.google_civic_candidate_name,
            'date_last_updated':            person.date_last_updated,
            'state_code':                   person.state_code,
            'we_vote_id':                   person.we_vote_id,
            'contest_office_name':          short_office_name,
            'party': party,
            'highlight': highlight,
        }
        people_list.append(person_item)

    template_values = {
        'number_of_rows':                   number_of_rows,
        'person_is_candidate':              is_candidate,
        'person_text':                      'Candidate' if is_candidate else 'Politician',
        'person_text_plural':               'Candidates' if is_candidate else 'Politicians',
        'people_list':                      people_list,
        'index_offset':                     start,
        'return_link':                      '/c/' if is_candidate else '/politician/',
    }
    return render(request, 'candidate/candidate_and_politician_name_fix_list.html', template_values)


def candidate_change_names(changes):
    count = 0
    for change in changes:
        try:
            candidate_query = CandidateCampaign.objects.filter(we_vote_id=change['we_vote_id'])
            candidate_query = candidate_query
            candidate_list = list(candidate_query)
            candidate = candidate_list[0]
            setattr(candidate, 'candidate_name', change['name_after'])
            timezone = pytz.timezone("America/Los_Angeles")
            datetime_now = timezone.localize(datetime.now())
            setattr(candidate, 'date_last_changed', datetime_now)
            candidate.save()
            count += 1
        except Exception as err:
            logger.error('candidate_change_names caught: ', err)
            count = -1

    return count


@login_required
def candidate_edit_process_view(request):
    """
    Process the new or edit candidate forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()

    status = ""
    look_for_politician = request.POST.get('look_for_politician', False)  # If this comes in with value, don't save
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    refresh_from_twitter = request.POST.get('refresh_from_twitter', False)

    candidate_id = convert_to_int(request.POST.get('candidate_id', 0))
    reject_twitter_link_possibility_id = convert_to_int(request.POST.get('reject_twitter_link_possibility_id', 0))
    redirect_to_candidate_list = positive_value_exists(request.POST.get('redirect_to_candidate_list', False))
    candidate_name = request.POST.get('candidate_name', False)
    google_civic_candidate_name = request.POST.get('google_civic_candidate_name', False)
    google_civic_candidate_name2 = request.POST.get('google_civic_candidate_name2', False)
    google_civic_candidate_name3 = request.POST.get('google_civic_candidate_name3', False)
    hide_candidate_tools = request.POST.get('hide_candidate_tools', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    candidate_twitter_handle = request.POST.get('candidate_twitter_handle', False)
    if positive_value_exists(candidate_twitter_handle):
        candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle)
    candidate_url = request.POST.get('candidate_url', False)
    candidate_contact_form_url = request.POST.get('candidate_contact_form_url', False)
    facebook_url = request.POST.get('facebook_url', False)
    candidate_email = request.POST.get('candidate_email', False)
    candidate_phone = request.POST.get('candidate_phone', False)
    contest_office_id = request.POST.get('contest_office_id', False)
    ballot_guide_official_statement = request.POST.get('ballot_guide_official_statement', False)
    party = request.POST.get('party', False)
    ballotpedia_candidate_id = request.POST.get('ballotpedia_candidate_id', False)
    ballotpedia_candidate_name = request.POST.get('ballotpedia_candidate_name', False)
    ballotpedia_candidate_url = request.POST.get('ballotpedia_candidate_url', False)
    ballotpedia_candidate_summary = request.POST.get('ballotpedia_candidate_summary', False)
    ballotpedia_office_id = request.POST.get('ballotpedia_office_id', False)
    ballotpedia_person_id = request.POST.get('ballotpedia_person_id', False)
    ballotpedia_race_id = request.POST.get('ballotpedia_race_id', False)
    vote_usa_politician_id = request.POST.get('vote_usa_politician_id', False)
    vote_usa_office_id = request.POST.get('vote_usa_office_id', False)
    photo_url_from_vote_usa = request.POST.get('photo_url_from_vote_usa', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    maplight_id = request.POST.get('maplight_id', False)
    page = convert_to_int(request.POST.get('page', 0))
    state_code = request.POST.get('state_code', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)
    profile_image_type_currently_active = request.POST.get('profile_image_type_currently_active', False)
    google_search_image_file = request.POST.get('google_search_image_file', False)
    google_search_link = request.POST.get('google_search_link', False)
    twitter_url = request.POST.get('twitter_url', False)
    withdrawal_date = request.POST.get('withdrawal_date', False)
    withdrawn_from_election = positive_value_exists(request.POST.get('withdrawn_from_election', False))
    do_not_display_on_ballot = positive_value_exists(request.POST.get('do_not_display_on_ballot', False))
    select_for_marking_twitter_link_possibility_ids = request.POST.getlist('select_for_marking_checks[]')
    which_marking = request.POST.get('which_marking')

    # Note: A date is not required, but if provided it needs to be in a correct date format
    if positive_value_exists(withdrawn_from_election) and positive_value_exists(withdrawal_date):
        # If withdrawn_from_election is true AND we have an invalid withdrawal_date return with error
        res = re.match(r'([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))', withdrawal_date)
        if res is None:
            print('withdrawal_date is invalid: ' + withdrawal_date)
            url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                            "&candidate_name=" + str(candidate_name) + \
                            "&state_code=" + str(state_code) + \
                            "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                            "&google_civic_candidate_name2=" + str(google_civic_candidate_name2) + \
                            "&google_civic_candidate_name3=" + str(google_civic_candidate_name3) + \
                            "&contest_office_id=" + str(contest_office_id) + \
                            "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                            "&candidate_url=" + str(candidate_url) + \
                            "&candidate_contact_form_url=" + str(candidate_contact_form_url) + \
                            "&facebook_url=" + str(facebook_url) + \
                            "&candidate_email=" + str(candidate_email) + \
                            "&candidate_phone=" + str(candidate_phone) + \
                            "&party=" + str(party) + \
                            "&ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                            "&vote_smart_id=" + str(vote_smart_id) + \
                            "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                            "&maplight_id=" + str(maplight_id)
            messages.add_message(request, messages.ERROR, 'Could not save candidate. If the "Candidate Has Withdrawn '
                                                          'From Election" is True, then the date in the field must be '
                                                          'in the YYYY-MM-DD format')
            if positive_value_exists(candidate_id):
                return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) + url_variables)
            else:
                return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) + url_variables)

    # Check to see if this candidate is already being used anywhere
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    state_code_from_candidate = ''
    candidate_we_vote_id = ''
    if positive_value_exists(candidate_id):
        # We don't put this in a try/except block because we want the page to fail if there's an error
        candidate_query = CandidateCampaign.objects.filter(id=candidate_id)
        if len(candidate_query):
            candidate_on_stage = candidate_query[0]
            candidate_we_vote_id = candidate_on_stage.we_vote_id
            state_code_from_candidate = candidate_on_stage.state_code
            candidate_on_stage_found = True

    # ##################################
    # Deleting or Adding a new CandidateToOfficeLink
    results = candidate_list_manager.retrieve_candidate_to_office_link_list(
        candidate_we_vote_id_list=[candidate_we_vote_id],
        read_only=False)
    candidate_to_office_link_list = results['candidate_to_office_link_list']
    for candidate_to_office_link in candidate_to_office_link_list:
        variable_name = "delete_candidate_to_office_link_" + str(candidate_to_office_link.id)
        candidate_to_office_link_delete_id = request.POST.get(variable_name, False)
        if positive_value_exists(candidate_to_office_link_delete_id):
            candidate_to_office_link.delete()
            messages.add_message(request, messages.INFO, 'Deleted Candidate-to-Office Link.')

    candidate_to_office_link_add_election = request.POST.get('candidate_to_office_link_add_election', False)
    candidate_to_office_link_add_state_code = request.POST.get('candidate_to_office_link_add_state_code', False)
    candidate_to_office_link_add_office_we_vote_id = request.POST.get('candidate_to_office_link_add_office_we_vote_id',
                                                                      False)
    if positive_value_exists(candidate_to_office_link_add_election) and \
            positive_value_exists(candidate_to_office_link_add_state_code) and \
            positive_value_exists(candidate_to_office_link_add_office_we_vote_id):
        candidate_to_office_link_add_election = candidate_to_office_link_add_election.strip()
        candidate_to_office_link_add_office_we_vote_id = candidate_to_office_link_add_office_we_vote_id.strip()
        candidate_to_office_link_add_state_code = candidate_to_office_link_add_state_code.strip()
        if positive_value_exists(candidate_we_vote_id):
            results = candidate_manager.get_or_create_candidate_to_office_link(
                candidate_we_vote_id=candidate_we_vote_id,
                contest_office_we_vote_id=candidate_to_office_link_add_office_we_vote_id,
                google_civic_election_id=candidate_to_office_link_add_election,
                state_code=candidate_to_office_link_add_state_code)
            if results['new_candidate_to_office_link_created']:
                messages.add_message(request, messages.INFO, 'Added Candidate-to-Office Link.')
            else:
                messages.add_message(request, messages.ERROR, 'Candidate-to-Office Link already exists.')
        else:
            messages.add_message(request, messages.ERROR,
                                 'Cannot add Candidate-to-Office Link: candidate_we_vote_id missing.')
    elif positive_value_exists(candidate_to_office_link_add_election) or \
            positive_value_exists(candidate_to_office_link_add_state_code) or \
            positive_value_exists(candidate_to_office_link_add_office_we_vote_id):
        messages.add_message(request, messages.ERROR, 'To add Candidate-to-Office Link, all three variables required.')

    # ##################################
    # If linked to a Politician, make sure that both politician_id and politician_we_vote_id exist
    if candidate_on_stage_found:
        if positive_value_exists(candidate_on_stage.politician_we_vote_id) \
                and not positive_value_exists(candidate_on_stage.politician_id):
            try:
                politician_manager = PoliticianManager()
                results = politician_manager.retrieve_politician(0, candidate_on_stage.politician_we_vote_id)
                if results['politician_found']:
                    politician = results['politician']
                    candidate_on_stage.politician_id = politician.id
                    candidate_on_stage.save()
                pass
            except Exception as e:
                print('Could not save candidate.', e)
                messages.add_message(request, messages.ERROR, 'Could not save candidate.')

    contest_office_we_vote_id = ''
    office_manager = ContestOfficeManager()
    state_code_from_office = ''
    if positive_value_exists(contest_office_id):
        results = office_manager.retrieve_contest_office_from_id(contest_office_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            contest_office_we_vote_id = contest_office.we_vote_id
            state_code_from_office = contest_office.state_code

    election_manager = ElectionManager()
    # Needed for new candidates
    election_results = election_manager.retrieve_election(google_civic_election_id)
    state_code_from_election = ""
    election_found = False
    if election_results['election_found']:
        election = election_results['election']
        election_found = election_results['election_found']
        state_code_from_election = election.get_election_state()

    if positive_value_exists(state_code_from_office):
        best_state_code = state_code_from_office
    elif positive_value_exists(state_code_from_candidate):
        best_state_code = state_code_from_candidate
    elif positive_value_exists(state_code_from_election):
        best_state_code = state_code_from_election
    else:
        best_state_code = state_code

    if positive_value_exists(look_for_politician):
        # If here, we specifically want to see if a politician exists, given the information submitted
        match_results = retrieve_candidate_politician_match_options(
            vote_smart_id=vote_smart_id,
            vote_usa_politician_id=vote_usa_politician_id,
            maplight_id=maplight_id,
            candidate_twitter_handle=candidate_twitter_handle,
            candidate_name=candidate_name,
            state_code=best_state_code)
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
                        "&google_civic_candidate_name2=" + str(google_civic_candidate_name2) + \
                        "&google_civic_candidate_name3=" + str(google_civic_candidate_name3) + \
                        "&contest_office_id=" + str(contest_office_id) + \
                        "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                        "&candidate_url=" + str(candidate_url) + \
                        "&candidate_contact_form_url=" + str(candidate_contact_form_url) + \
                        "&facebook_url=" + str(facebook_url) + \
                        "&candidate_email=" + str(candidate_email) + \
                        "&candidate_phone=" + str(candidate_phone) + \
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
            if positive_value_exists(ballotpedia_candidate_id):
                at_least_one_filter = True
                filter_list |= Q(ballotpedia_candidate_id=ballotpedia_candidate_id)
            if positive_value_exists(maplight_id):
                at_least_one_filter = True
                filter_list |= Q(maplight_id=maplight_id)
            if positive_value_exists(vote_smart_id):
                at_least_one_filter = True
                filter_list |= Q(vote_smart_id=vote_smart_id)

            if at_least_one_filter:
                candidate_duplicates_query = CandidateCampaign.objects.filter(filter_list)
                if positive_value_exists(google_civic_election_id):
                    google_civic_election_id_list = [google_civic_election_id]
                    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
                        google_civic_election_id_list=google_civic_election_id_list,
                        limit_to_this_state_code=state_code)
                    candidate_we_vote_id_list = results['candidate_we_vote_id_list']
                    candidate_duplicates_query = candidate_duplicates_query.filter(
                        we_vote_id__in=candidate_we_vote_id_list)

                if len(candidate_duplicates_query):
                    existing_candidate_found = True
        except Exception as e:
            pass

    try:
        if existing_candidate_found:
            # We have found a duplicate for this election
            messages.add_message(request, messages.ERROR, 'This candidate is already saved for this election.')
            url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                            "&candidate_name=" + str(candidate_name) + \
                            "&state_code=" + str(state_code) + \
                            "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                            "&google_civic_candidate_name2=" + str(google_civic_candidate_name2) + \
                            "&google_civic_candidate_name3=" + str(google_civic_candidate_name3) + \
                            "&contest_office_id=" + str(contest_office_id) + \
                            "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                            "&candidate_url=" + str(candidate_url) + \
                            "&candidate_contact_form_url=" + str(candidate_contact_form_url) + \
                            "&facebook_url=" + str(facebook_url) + \
                            "&candidate_email=" + str(candidate_email) + \
                            "&candidate_phone=" + str(candidate_phone) + \
                            "&party=" + str(party) + \
                            "&ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                            "&ballotpedia_candidate_id=" + str(ballotpedia_candidate_id) + \
                            "&ballotpedia_candidate_name=" + str(ballotpedia_candidate_name) + \
                            "&ballotpedia_candidate_url=" + str(ballotpedia_candidate_url) + \
                            "&vote_smart_id=" + str(vote_smart_id) + \
                            "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                            "&maplight_id=" + str(maplight_id)
            return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) + url_variables)
        elif candidate_on_stage_found:
            # Update
            if candidate_name is not False:
                candidate_on_stage.candidate_name = candidate_name
            if candidate_twitter_handle is not False:
                candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
            if candidate_url is not False:
                candidate_on_stage.candidate_url = candidate_url
            if candidate_contact_form_url is not False:
                candidate_on_stage.candidate_contact_form_url = candidate_contact_form_url
            if facebook_url is not False:
                candidate_on_stage.facebook_url = facebook_url
            if candidate_email is not False:
                candidate_on_stage.candidate_email = candidate_email
            if candidate_phone is not False:
                candidate_on_stage.candidate_phone = candidate_phone
            if party is not False:
                candidate_on_stage.party = party
            if ballot_guide_official_statement is not False:
                candidate_on_stage.ballot_guide_official_statement = ballot_guide_official_statement
            if ballotpedia_candidate_id is not False:
                candidate_on_stage.ballotpedia_candidate_id = convert_to_int(ballotpedia_candidate_id)
            if ballotpedia_candidate_name is not False:
                candidate_on_stage.ballotpedia_candidate_name = ballotpedia_candidate_name
            if ballotpedia_candidate_url is not False:
                candidate_on_stage.ballotpedia_candidate_url = ballotpedia_candidate_url
            if ballotpedia_candidate_summary is not False:
                candidate_on_stage.ballotpedia_candidate_summary = ballotpedia_candidate_summary
            if ballotpedia_office_id is not False:
                candidate_on_stage.ballotpedia_office_id = convert_to_int(ballotpedia_office_id)
            if ballotpedia_person_id is not False:
                candidate_on_stage.ballotpedia_person_id = convert_to_int(ballotpedia_person_id)
            if ballotpedia_race_id is not False:
                candidate_on_stage.ballotpedia_race_id = convert_to_int(ballotpedia_race_id)
            if photo_url_from_vote_usa is not False:
                candidate_on_stage.photo_url_from_vote_usa = photo_url_from_vote_usa
            if vote_smart_id is not False:
                candidate_on_stage.vote_smart_id = vote_smart_id
            if vote_usa_politician_id is not False:
                candidate_on_stage.vote_usa_politician_id = vote_usa_politician_id
            if vote_usa_office_id is not False:
                candidate_on_stage.vote_usa_office_id = vote_usa_office_id
            if maplight_id is not False:
                candidate_on_stage.maplight_id = maplight_id
            if google_civic_candidate_name is not False:
                candidate_on_stage.google_civic_candidate_name = google_civic_candidate_name
            if google_civic_candidate_name2 is not False:
                candidate_on_stage.google_civic_candidate_name2 = google_civic_candidate_name2
            if google_civic_candidate_name3 is not False:
                candidate_on_stage.google_civic_candidate_name3 = google_civic_candidate_name3
            if state_code is not False:
                candidate_on_stage.state_code = state_code
            if twitter_url is not False:
                candidate_on_stage.twitter_url = twitter_url
            candidate_on_stage.withdrawn_from_election = withdrawn_from_election
            if withdrawn_from_election:
                if positive_value_exists(withdrawal_date):
                    candidate_on_stage.withdrawal_date = withdrawal_date
                else:
                    candidate_on_stage.withdrawal_date = None
            candidate_on_stage.do_not_display_on_ballot = do_not_display_on_ballot

            if google_search_image_file:
                # If google search image exist then cache master and resized images and save them to candidate table
                results = save_image_to_candidate_table(
                    candidate=candidate_on_stage,
                    image_url=google_search_image_file,
                    source_link=google_search_link,
                    url_is_broken=False,
                    kind_of_source_website=None)
                if not positive_value_exists(results['success']):
                    status += results['status']
                google_search_user_manager = GoogleSearchUserManager()
                google_search_user_results = google_search_user_manager.retrieve_google_search_user_from_item_link(
                    candidate_on_stage.we_vote_id, google_search_link)
                if google_search_user_results['google_search_user_found']:
                    google_search_user = google_search_user_results['google_search_user']
                    google_search_user.chosen_and_updated = True
                    google_search_user.save()
            elif google_search_link:
                # save google search link
                save_google_search_link_to_candidate_table(candidate_on_stage, google_search_link)

            # Check to see if this is a We Vote-created election
            # is_we_vote_google_civic_election_id = True \
            #     if convert_to_int(candidate_on_stage.google_civic_election_id) >= 1000000 \
            #     else False

            if profile_image_type_currently_active is not False:
                if profile_image_type_currently_active in [
                        PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN,
                        PROFILE_IMAGE_TYPE_UPLOADED, PROFILE_IMAGE_TYPE_VOTE_USA]:
                    candidate_on_stage.profile_image_type_currently_active = profile_image_type_currently_active
                    if profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
                        candidate_on_stage.we_vote_hosted_profile_image_url_large = \
                            candidate_on_stage.we_vote_hosted_profile_facebook_image_url_large
                        candidate_on_stage.we_vote_hosted_profile_image_url_medium = \
                            candidate_on_stage.we_vote_hosted_profile_facebook_image_url_medium
                        candidate_on_stage.we_vote_hosted_profile_image_url_tiny = \
                            candidate_on_stage.we_vote_hosted_profile_facebook_image_url_tiny
                    elif profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
                        candidate_on_stage.we_vote_hosted_profile_image_url_large = \
                            candidate_on_stage.we_vote_hosted_profile_twitter_image_url_large
                        candidate_on_stage.we_vote_hosted_profile_image_url_medium = \
                            candidate_on_stage.we_vote_hosted_profile_twitter_image_url_medium
                        candidate_on_stage.we_vote_hosted_profile_image_url_tiny = \
                            candidate_on_stage.we_vote_hosted_profile_twitter_image_url_tiny
                    elif profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UPLOADED:
                        candidate_on_stage.we_vote_hosted_profile_image_url_large = \
                            candidate_on_stage.we_vote_hosted_profile_uploaded_image_url_large
                        candidate_on_stage.we_vote_hosted_profile_image_url_medium = \
                            candidate_on_stage.we_vote_hosted_profile_uploaded_image_url_medium
                        candidate_on_stage.we_vote_hosted_profile_image_url_tiny = \
                            candidate_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny
                    elif profile_image_type_currently_active == PROFILE_IMAGE_TYPE_VOTE_USA:
                        candidate_on_stage.we_vote_hosted_profile_image_url_large = \
                            candidate_on_stage.we_vote_hosted_profile_vote_usa_image_url_large
                        candidate_on_stage.we_vote_hosted_profile_image_url_medium = \
                            candidate_on_stage.we_vote_hosted_profile_vote_usa_image_url_medium
                        candidate_on_stage.we_vote_hosted_profile_image_url_tiny = \
                            candidate_on_stage.we_vote_hosted_profile_vote_usa_image_url_tiny

            candidate_on_stage.save()

            ballotpedia_image_id = candidate_on_stage.ballotpedia_image_id
            ballotpedia_profile_image_url_https = candidate_on_stage.ballotpedia_profile_image_url_https
            # Now refresh the cache entries for this candidate

            messages.add_message(request, messages.INFO, 'CandidateCampaign updated.')
        else:
            # Create new
            # election must be found
            if not election_found or not positive_value_exists(contest_office_we_vote_id):
                messages.add_message(request, messages.ERROR,
                                     'Could not find election or office -- required to save candidate.')
                url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                                "&state_code=" + str(state_code)
                return HttpResponseRedirect(reverse('office:office_list', args=()) + url_variables)

            required_candidate_variables = True \
                if positive_value_exists(candidate_name) and positive_value_exists(contest_office_id) \
                else False
            if required_candidate_variables:
                candidate_on_stage = CandidateCampaign(
                    candidate_name=candidate_name,
                    state_code=best_state_code,
                )
                if google_civic_candidate_name is not False:
                    candidate_on_stage.google_civic_candidate_name = google_civic_candidate_name
                if google_civic_candidate_name2 is not False:
                    candidate_on_stage.google_civic_candidate_name2 = google_civic_candidate_name2
                if google_civic_candidate_name3 is not False:
                    candidate_on_stage.google_civic_candidate_name3 = google_civic_candidate_name3
                if candidate_twitter_handle is not False:
                    candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
                if twitter_url is not False:
                    candidate_on_stage.twitter_url = twitter_url
                if withdrawn_from_election:
                    candidate_on_stage.withdrawn_from_election = withdrawn_from_election
                    candidate_on_stage.withdrawal_date = withdrawal_date
                if do_not_display_on_ballot:
                    candidate_on_stage.do_not_display_on_ballot = do_not_display_on_ballot
                if candidate_url is not False:
                    candidate_on_stage.candidate_url = candidate_url
                if candidate_contact_form_url is not False:
                    candidate_on_stage.candidate_contact_form_url = candidate_contact_form_url
                if facebook_url is not False:
                    candidate_on_stage.facebook_url = facebook_url
                if candidate_email is not False:
                    candidate_on_stage.candidate_email = candidate_email
                if candidate_phone is not False:
                    candidate_on_stage.candidate_phone = candidate_phone
                if party is not False:
                    candidate_on_stage.party = party
                if ballot_guide_official_statement is not False:
                    candidate_on_stage.ballot_guide_official_statement = ballot_guide_official_statement
                if ballotpedia_candidate_id is not False:
                    candidate_on_stage.ballotpedia_candidate_id = convert_to_int(ballotpedia_candidate_id)
                if ballotpedia_candidate_name is not False:
                    candidate_on_stage.ballotpedia_candidate_name = ballotpedia_candidate_name
                if ballotpedia_candidate_url is not False:
                    candidate_on_stage.ballotpedia_candidate_url = ballotpedia_candidate_url
                if ballotpedia_candidate_summary is not False:
                    candidate_on_stage.ballotpedia_candidate_summary = ballotpedia_candidate_summary
                if ballotpedia_office_id is not False:
                    candidate_on_stage.ballotpedia_office_id = convert_to_int(ballotpedia_office_id)
                if ballotpedia_person_id is not False:
                    candidate_on_stage.ballotpedia_person_id = convert_to_int(ballotpedia_person_id)
                if ballotpedia_race_id is not False:
                    candidate_on_stage.ballotpedia_race_id = convert_to_int(ballotpedia_race_id)
                if photo_url_from_vote_usa is not False:
                    candidate_on_stage.photo_url_from_vote_usa = photo_url_from_vote_usa
                if vote_smart_id is not False:
                    candidate_on_stage.vote_smart_id = vote_smart_id
                if vote_usa_politician_id is not False:
                    candidate_on_stage.vote_usa_politician_id = vote_usa_politician_id
                if vote_usa_office_id is not False:
                    candidate_on_stage.vote_usa_office_id = vote_usa_office_id
                if maplight_id is not False:
                    candidate_on_stage.maplight_id = maplight_id
                if politician_we_vote_id is not False:
                    candidate_on_stage.politician_we_vote_id = politician_we_vote_id

                candidate_on_stage.save()
                candidate_id = candidate_on_stage.id
                candidate_we_vote_id = candidate_on_stage.we_vote_id
                ballotpedia_image_id = candidate_on_stage.ballotpedia_image_id
                ballotpedia_profile_image_url_https = candidate_on_stage.ballotpedia_profile_image_url_https
                messages.add_message(request, messages.INFO, 'New candidate saved.')

                # Now add Candidate to Office Link
                candidate_manager.get_or_create_candidate_to_office_link(
                    candidate_we_vote_id=candidate_we_vote_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    state_code=best_state_code)
            else:
                # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
                url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                                "&candidate_name=" + str(candidate_name) + \
                                "&state_code=" + str(best_state_code) + \
                                "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                                "&google_civic_candidate_name2=" + str(google_civic_candidate_name2) + \
                                "&google_civic_candidate_name3=" + str(google_civic_candidate_name3) + \
                                "&contest_office_id=" + str(contest_office_id) + \
                                "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                                "&candidate_url=" + str(candidate_url) + \
                                "&candidate_contact_form_url=" + str(candidate_contact_form_url) + \
                                "&facebook_url=" + str(facebook_url) + \
                                "&candidate_email=" + str(candidate_email) + \
                                "&candidate_phone=" + str(candidate_phone) + \
                                "&party=" + str(party) + \
                                "&ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                                "&ballotpedia_candidate_id=" + str(ballotpedia_candidate_id) + \
                                "&ballotpedia_candidate_name=" + str(ballotpedia_candidate_name) + \
                                "&ballotpedia_candidate_url=" + str(ballotpedia_candidate_url) + \
                                "&ballotpedia_office_id=" + str(ballotpedia_office_id) + \
                                "&ballotpedia_person_id=" + str(ballotpedia_person_id) + \
                                "&ballotpedia_race_id=" + str(ballotpedia_race_id) + \
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
        print('Could not save candidate (2).', e)
        messages.add_message(request, messages.ERROR, 'Could not save candidate (2), error: {error}'
                                                      ''.format(error=str(e)))
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    # if positive_value_exists(ballotpedia_image_id) and not positive_value_exists(ballotpedia_profile_image_url_https):
    #     results = retrieve_and_save_ballotpedia_candidate_images(candidate_on_stage)

    if positive_value_exists(refresh_from_twitter):
        results = refresh_twitter_candidate_details(candidate_on_stage)
    # elif profile_image_type_currently_active == 'UNKNOWN':
    #     # Prevent Twitter from updating
    #     pass
    elif positive_value_exists(candidate_twitter_handle):
        results = refresh_twitter_candidate_details(candidate_on_stage)

    # Make sure 'which_marking' is one of the allowed Filter fields
    if positive_value_exists(which_marking) \
            and which_marking not in ("not_a_match", "possible_match"):
        messages.add_message(request, messages.ERROR,
                             'The filter you are trying to update is not recognized: {which_marking}'
                             ''.format(which_marking=which_marking))

    show_all_twitter_search_results = 0
    twitter_manager = TwitterUserManager()
    if positive_value_exists(reject_twitter_link_possibility_id):
        try:
            defaults = {
                'not_a_match': True,
            }
            results = twitter_manager.update_or_create_twitter_link_possibility(
                twitter_link_possibility_id=reject_twitter_link_possibility_id,
                defaults=defaults)
            show_all_twitter_search_results = 1
            if results['success']:
                messages.add_message(request, messages.INFO, 'TwitterLinkPossibility marked as not a match.')
            else:
                messages.add_message(request, messages.ERROR,
                                     'TwitterLinkPossibility {results}'
                                     ''.format(results=results))
        except ValueError:
            messages.add_message(request, messages.ERROR,
                                 'Bad id: {reject_twitter_link_possibility_id}'
                                 ''.format(reject_twitter_link_possibility_id=reject_twitter_link_possibility_id))
    elif positive_value_exists(which_marking):
        items_processed_successfully = 0
        update = False
        not_a_match = False
        if which_marking == 'not_a_match':
            not_a_match = True
            update = True
        elif which_marking == 'possible_match':
            not_a_match = False
            update = True
        if update:
            for twitter_link_possibility_id_string in select_for_marking_twitter_link_possibility_ids:
                try:
                    twitter_link_possibility_id = int(twitter_link_possibility_id_string)
                    defaults = {
                        'not_a_match': not_a_match,
                    }
                    results = twitter_manager.update_or_create_twitter_link_possibility(
                        twitter_link_possibility_id=twitter_link_possibility_id,
                        defaults=defaults)
                    show_all_twitter_search_results = 1
                    if results['success']:
                        items_processed_successfully += 1
                    else:
                        messages.add_message(request, messages.ERROR,
                                             'TwitterLinkPossibility {results}'
                                             ''.format(results=results))
                except ValueError:
                    messages.add_message(request, messages.ERROR,
                                         'Bad id for: {voter_guide_possibility_id_string}')

        messages.add_message(request, messages.INFO,
                             'TwitterLinkPossibility processed successfully: {items_processed_successfully}'
                             ''.format(items_processed_successfully=items_processed_successfully))

    url_variables = "?null=1"
    if positive_value_exists(show_all_twitter_search_results):
        url_variables += "&show_all_twitter_search_results=1#twitter_link_possibility_list"

    if redirect_to_candidate_list:
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&show_candidates_with_twitter_options=1' +
                                    '&page=' + str(page))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))
    else:
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                    url_variables)


@login_required
def candidate_politician_match_view(request):
    """
    Try to match the current candidate to an existing politician entry. If a politician entry isn't found,
    create an entry.
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = request.GET.get('candidate_id', 0)
    candidate_id = convert_to_int(candidate_id)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')
    # google_civic_election_id is included for interface usability reasons and isn't used in the processing
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    we_vote_candidate = None

    candidate_manager = CandidateManager()
    if positive_value_exists(candidate_we_vote_id):
        results = candidate_manager.retrieve_candidate(candidate_we_vote_id=candidate_we_vote_id)
        if not positive_value_exists(results['candidate_found']):
            messages.add_message(request, messages.ERROR,
                                 "Candidate '{candidate_we_vote_id}' not found."
                                 "".format(candidate_we_vote_id=candidate_we_vote_id))
            return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_we_vote_id,)))
        we_vote_candidate = results['candidate']
    elif positive_value_exists(candidate_id):
        results = candidate_manager.retrieve_candidate_from_id(candidate_id)
        if not positive_value_exists(results['candidate_found']):
            messages.add_message(request, messages.ERROR,
                                 "Candidate '{candidate_id}' not found.".format(candidate_id=candidate_id))
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))
        we_vote_candidate = results['candidate']
    else:
        messages.add_message(request, messages.ERROR, "Candidate identifier was not passed in.")
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    # Try to find existing politician for this candidate. If none found, create politician.
    results = candidate_politician_match(we_vote_candidate)

    display_messages = True
    if results['status'] and display_messages:
        messages.add_message(request, messages.INFO, results['status'])
    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def candidate_politician_match_this_election_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_list = []
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id_list = [google_civic_election_id]
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', '')

    # We only want to process if a google_civic_election_id comes in
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()))

    try:
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list)
        # if not positive_value_exists(results['success']):
        #     status += results['status']
        #     success = False
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

        candidate_query = CandidateCampaign.objects.order_by('candidate_name')
        candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
        if positive_value_exists(state_code):
            candidate_query = candidate_query.filter(state_code__iexact=state_code)
        candidate_list = list(candidate_query)
    except CandidateCampaign.DoesNotExist:
        messages.add_message(request, messages.INFO, "No candidates found for this election: {id}.".format(
            id=google_civic_election_id))
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}"
                                                                                   "".format(
                                                                                   var=google_civic_election_id))

    num_candidates_reviewed = 0
    num_that_already_have_politician_we_vote_id = 0
    new_politician_created = 0
    existing_politician_found = 0
    multiple_politicians_found = 0
    other_results = 0

    message = "About to loop through all of the candidates in this election to make sure we have a politician record."
    print_to_log(logger, exception_message_optional=message)

    # Loop through all of the candidates in this election
    for we_vote_candidate in candidate_list:
        num_candidates_reviewed += 1
        if we_vote_candidate.politician_we_vote_id:
            num_that_already_have_politician_we_vote_id += 1
        match_results = candidate_politician_match(we_vote_candidate)
        if match_results['politician_created']:
            new_politician_created += 1
        elif match_results['politician_found']:
            existing_politician_found += 1
        elif match_results['politician_list_found']:
            multiple_politicians_found += 1
        else:
            other_results += 1

    message = "Google Civic Election ID: {election_id}, " \
              "{num_candidates_reviewed} candidates reviewed, " \
              "{num_that_already_have_politician_we_vote_id} Candidates that already have Politician Ids, " \
              "{new_politician_created} politicians just created, " \
              "{existing_politician_found} politicians found that already exist, " \
              "{multiple_politicians_found} times we found multiple politicians and could not link, " \
              "{other_results} other results". \
              format(election_id=google_civic_election_id,
                     num_candidates_reviewed=num_candidates_reviewed,
                     num_that_already_have_politician_we_vote_id=num_that_already_have_politician_we_vote_id,
                     new_politician_created=new_politician_created,
                     existing_politician_found=existing_politician_found,
                     multiple_politicians_found=multiple_politicians_found,
                     other_results=other_results)

    print_to_log(logger, exception_message_optional=message)
    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                "?google_civic_election_id={google_civic_election_id}"
                                "&state_code={state_code}"
                                "".format(
                                google_civic_election_id=google_civic_election_id,
                                state_code=state_code))


@login_required
def candidate_retrieve_photos_view(request, candidate_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(candidate_id)
    force_retrieve = request.GET.get('force_retrieve', 0)

    candidate_manager = CandidateManager()

    results = candidate_manager.retrieve_candidate_from_id(candidate_id)
    if not positive_value_exists(results['candidate_found']):
        messages.add_message(request, messages.ERROR,
                             "Candidate '{candidate_id}' not found.".format(candidate_id=candidate_id))
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    we_vote_candidate = results['candidate']

    display_messages = True
    retrieve_candidate_results = retrieve_candidate_photos(we_vote_candidate, force_retrieve)

    if retrieve_candidate_results['status'] and display_messages:
        messages.add_message(request, messages.INFO, retrieve_candidate_results['status'])
    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))


@login_required
def candidate_merge_process_view(request):
    """
    Process the merging of two candidates
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateManager()

    merge = request.POST.get('merge', False)
    skip = request.POST.get('skip', False)

    # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
    candidate1_we_vote_id = request.POST.get('candidate1_we_vote_id', 0)
    candidate2_we_vote_id = request.POST.get('candidate2_we_vote_id', 0)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    redirect_to_candidate_list = request.POST.get('redirect_to_candidate_list', False)
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    state_code = request.POST.get('state_code', '')

    if positive_value_exists(skip):
        results = candidate_manager.update_or_create_candidates_are_not_duplicates(
            candidate1_we_vote_id, candidate2_we_vote_id)
        if not results['new_candidates_are_not_duplicates_created']:
            messages.add_message(request, messages.ERROR, 'Could not save candidates_are_not_duplicates entry: ' +
                                 results['status'])
        messages.add_message(request, messages.INFO, 'Prior candidates skipped, and not merged.')
        return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    candidate1_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate1_we_vote_id)
    if candidate1_results['candidate_found']:
        candidate1_on_stage = candidate1_results['candidate']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve candidate 1.')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    candidate2_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate2_we_vote_id)
    if candidate2_results['candidate_found']:
        candidate2_on_stage = candidate2_results['candidate']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve candidate 2.')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    # Gather choices made from merge form
    conflict_values = figure_out_candidate_conflict_values(candidate1_on_stage, candidate2_on_stage)
    admin_merge_choices = {}
    for attribute in CANDIDATE_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            choice = request.POST.get(attribute + '_choice', '')
            if candidate2_we_vote_id == choice:
                admin_merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
        elif conflict_value == "CANDIDATE2":
            admin_merge_choices[attribute] = getattr(candidate2_on_stage, attribute)

    merge_results = merge_these_two_candidates(candidate1_we_vote_id, candidate2_we_vote_id, admin_merge_choices)

    if positive_value_exists(merge_results['candidates_merged']):
        candidate = merge_results['candidate']
        messages.add_message(request, messages.INFO, "Candidate '{candidate_name}' merged."
                                                     "".format(candidate_name=candidate.candidate_name))
    else:
        # NOTE: We could also redirect to a page to look specifically at these two candidates, but this should
        # also get you back to looking at the two candidates
        messages.add_message(request, messages.ERROR, merge_results['status'])
        return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&auto_merge_off=1" +
                                    "&state_code=" + str(state_code))

    if redirect_to_candidate_list:
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate1_on_stage.id,)))


@login_required
def find_and_merge_duplicate_candidates_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    ignore_candidate_id_list = []
    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', "")
    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()
    election_manager = ElectionManager()

    if positive_value_exists(google_civic_election_id):
        google_civic_election_id_list = [google_civic_election_id]
    else:
        results = election_manager.retrieve_upcoming_google_civic_election_id_list()
        google_civic_election_id_list = results['upcoming_google_civic_election_id_list']

    results = candidate_list_manager.retrieve_candidates_for_specific_elections(
        google_civic_election_id_list=google_civic_election_id_list,
        return_list_of_objects=True)
    candidate_list = results['candidate_list_objects']

    # Loop through all of the candidates in this election to see how many have possible duplicates
    if positive_value_exists(find_number_of_duplicates):
        duplicate_candidate_count = 0
        for we_vote_candidate in candidate_list:
            # Note that we don't reset the ignore_candidate_list, so we don't search for a duplicate both directions
            ignore_candidate_id_list.append(we_vote_candidate.we_vote_id)
            duplicate_candidate_count_temp = fetch_duplicate_candidate_count(we_vote_candidate,
                                                                             ignore_candidate_id_list)
            duplicate_candidate_count += duplicate_candidate_count_temp

        if positive_value_exists(duplicate_candidate_count):
            messages.add_message(request, messages.INFO, "There are approximately {duplicate_candidate_count} "
                                                         "possible duplicates."
                                                         "".format(duplicate_candidate_count=duplicate_candidate_count))

    # Loop through all of the candidates in this election
    ignore_candidate_id_list = []
    for we_vote_candidate in candidate_list:
        # Add current candidate entry to the ignore list
        ignore_candidate_id_list.append(we_vote_candidate.we_vote_id)
        # Now check to for other candidates we have labeled as "not a duplicate"
        not_a_duplicate_list = candidate_manager.fetch_candidates_are_not_duplicates_list_we_vote_ids(
            we_vote_candidate.we_vote_id)

        ignore_candidate_id_list += not_a_duplicate_list

        results = find_duplicate_candidate(we_vote_candidate, ignore_candidate_id_list)
        ignore_candidate_id_list = []

        # If we find candidates to merge, stop and ask for confirmation (if we need to)
        if results['candidate_merge_possibility_found']:
            candidate_option1_for_template = we_vote_candidate
            candidate_option2_for_template = results['candidate_merge_possibility']

            # Can we automatically merge these candidates?
            merge_results = merge_if_duplicate_candidates(
                candidate_option1_for_template,
                candidate_option2_for_template,
                results['candidate_merge_conflict_values'])
            messages.add_message(request, messages.INFO, merge_results['status'])

            if merge_results['candidates_merged']:
                candidate = merge_results['candidate']
                messages.add_message(request, messages.INFO, "Candidate {candidate_name} automatically merged."
                                                             "".format(candidate_name=candidate.candidate_name))
                # return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                #                             "?google_civic_election_id=" + str(google_civic_election_id) +
                #                             "&state_code=" + str(state_code))
            else:
                # This view function takes us to displaying a template
                remove_duplicate_process = True  # Try to find another candidate to merge after finishing
                return render_candidate_merge_form(request, candidate_option1_for_template,
                                                   candidate_option2_for_template,
                                                   results['candidate_merge_conflict_values'], remove_duplicate_process)

    message = "Google Civic Election ID: {election_id}, " \
              "No duplicate candidates found for this election." \
              "".format(election_id=google_civic_election_id)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                "?google_civic_election_id={google_civic_election_id}"
                                "&state_code={state_code}"
                                "".format(
                                    google_civic_election_id=google_civic_election_id,
                                    state_code=state_code))


def render_candidate_merge_form(
        request, candidate_option1_for_template, candidate_option2_for_template,
        candidate_merge_conflict_values, remove_duplicate_process=True):

    state_code = ''
    if hasattr(candidate_option1_for_template, 'state_code'):
        state_code = candidate_option1_for_template.state_code
    if hasattr(candidate_option2_for_template, 'state_code'):
        state_code = candidate_option2_for_template.state_code

    bookmark_item_list_manager = BookmarkItemList()
    candidate_list_manager = CandidateListManager()
    position_list_manager = PositionListManager()

    # Get positions counts for both candidates
    candidate_option1_for_template.public_positions_count = \
        position_list_manager.fetch_public_positions_count_for_candidate(
            candidate_option1_for_template.id, candidate_option1_for_template.we_vote_id)
    candidate_option1_for_template.friends_positions_count = \
        position_list_manager.fetch_friends_only_positions_count_for_candidate(
            candidate_option1_for_template.id, candidate_option1_for_template.we_vote_id)
    # Bookmarks
    bookmark_results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_candidate(
        candidate_option1_for_template.we_vote_id)
    if bookmark_results['bookmark_item_list_found']:
        bookmark_item_list = bookmark_results['bookmark_item_list']
        candidate_option1_bookmark_count = len(bookmark_item_list)
    else:
        candidate_option1_bookmark_count = 0
    candidate_option1_for_template.bookmarks_count = candidate_option1_bookmark_count

    candidate_option2_for_template.public_positions_count = \
        position_list_manager.fetch_public_positions_count_for_candidate(
            candidate_option2_for_template.id, candidate_option2_for_template.we_vote_id)
    candidate_option2_for_template.friends_positions_count = \
        position_list_manager.fetch_friends_only_positions_count_for_candidate(
            candidate_option2_for_template.id, candidate_option2_for_template.we_vote_id)
    # Bookmarks
    bookmark_results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_candidate(
        candidate_option2_for_template.we_vote_id)
    if bookmark_results['bookmark_item_list_found']:
        bookmark_item_list = bookmark_results['bookmark_item_list']
        candidate_option2_bookmark_count = len(bookmark_item_list)
    else:
        candidate_option2_bookmark_count = 0
    candidate_option2_for_template.bookmarks_count = candidate_option2_bookmark_count

    # Which elections is this candidate in?
    results = candidate_list_manager.retrieve_candidate_to_office_link_list(
        candidate_we_vote_id_list=[candidate_option1_for_template.we_vote_id])
    candidate_option1_candidate_to_office_link_list = results['candidate_to_office_link_list']
    results = candidate_list_manager.retrieve_candidate_to_office_link_list(
        candidate_we_vote_id_list=[candidate_option2_for_template.we_vote_id])
    candidate_option2_candidate_to_office_link_list = results['candidate_to_office_link_list']

    contest_office_mismatch = True
    for option1_link in candidate_option1_candidate_to_office_link_list:
        for option2_link in candidate_option2_candidate_to_office_link_list:
            if option1_link.contest_office_we_vote_id == option2_link.contest_office_we_vote_id:
                contest_office_mismatch = False

    messages_on_stage = get_messages(request)
    template_values = {
        'candidate_option1':                                candidate_option1_for_template,
        'candidate_option2':                                candidate_option2_for_template,
        'candidate_option1_candidate_to_office_link_list':  candidate_option1_candidate_to_office_link_list,
        'candidate_option2_candidate_to_office_link_list':  candidate_option2_candidate_to_office_link_list,
        'conflict_values':                                  candidate_merge_conflict_values,
        'contest_office_mismatch':                          contest_office_mismatch,
        'google_civic_election_id':                         candidate_option1_for_template.google_civic_election_id,
        'messages_on_stage':                                messages_on_stage,
        'remove_duplicate_process':                         remove_duplicate_process,
        'state_code':                                       state_code,
    }
    return render(request, 'candidate/candidate_merge.html', template_values)


@login_required
def find_duplicate_candidate_view(request, candidate_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    number_of_duplicate_candidates_processed = 0
    number_of_duplicate_candidates_failed = 0
    number_of_duplicates_could_not_process = 0

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_manager = CandidateManager()
    candidate_results = candidate_manager.retrieve_candidate_from_id(candidate_id)
    if not candidate_results['candidate_found']:
        messages.add_message(request, messages.ERROR, "Candidate not found.")
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    candidate = candidate_results['candidate']

    ignore_candidate_id_list = []
    ignore_candidate_id_list.append(candidate.we_vote_id)

    results = find_duplicate_candidate(candidate, ignore_candidate_id_list)

    # If we find candidates to merge, stop and ask for confirmation
    if results['candidate_merge_possibility_found']:
        candidate_option1_for_template = candidate
        candidate_option2_for_template = results['candidate_merge_possibility']

        # This view function takes us to displaying a template
        remove_duplicate_process = True  # Try to find another candidate to merge after finishing
        return render_candidate_merge_form(request, candidate_option1_for_template, candidate_option2_for_template,
                                           results['candidate_merge_conflict_values'], remove_duplicate_process)

    message = "Duplicate Candidate: Google Civic Election ID: {election_id}, " \
              "{number_of_duplicate_candidates_processed} duplicates processed, " \
              "{number_of_duplicate_candidates_failed} duplicate merges failed, " \
              "{number_of_duplicates_could_not_process} could not be processed " \
              "".format(election_id=google_civic_election_id,
                        number_of_duplicate_candidates_processed=number_of_duplicate_candidates_processed,
                        number_of_duplicate_candidates_failed=number_of_duplicate_candidates_failed,
                        number_of_duplicates_could_not_process=number_of_duplicates_could_not_process)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                "?google_civic_election_id={var}".format(
                                var=google_civic_election_id))


@login_required
def remove_duplicate_candidate_view(request):
    """
    We use this view to semi-automate the process of finding candidate duplicates. Exact
    copies can be deleted automatically, and similar entries can be manually reviewed and deleted.
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    candidate_id = request.GET.get('candidate_id', 0)

    remove_duplicate_process = request.GET.get('remove_duplicate_process', False)

    missing_variables = False

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        missing_variables = True
    if not positive_value_exists(candidate_id):
        messages.add_message(request, messages.ERROR, "Candidate ID required.")
        missing_variables = True

    if missing_variables:
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}"
                                                                                   "".format(
            var=google_civic_election_id))

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.remove_duplicate_candidate(candidate_id, google_civic_election_id)
    if results['success']:
        if remove_duplicate_process:
            # Continue this process
            return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                                        "?google_civic_election_id=" + google_civic_election_id)
        else:
            messages.add_message(request, messages.ERROR, results['status'])
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))
    else:
        messages.add_message(request, messages.ERROR, "Could not remove candidate {candidate_id} '{candidate_name}'."
                                                      "".format(candidate_id=candidate_id,
                                                                candidate_name=candidate_id))  # TODO Add candidate_name
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}"
                                                                                   "".format(
            var=google_civic_election_id))


@login_required
def retrieve_candidate_photos_for_election_view(request, election_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_list = []
    google_civic_election_id = convert_to_int(election_id)

    # We only want to process if a google_civic_election_id comes in
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()))

    candidate_list_manager = CandidateListManager()
    google_civic_election_id_list = [str(google_civic_election_id)]
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
        google_civic_election_id_list=google_civic_election_id_list)
    candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    try:
        candidate_query = CandidateCampaign.objects.order_by('candidate_name')
        candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
        candidate_list = list(candidate_query)
    except CandidateCampaign.DoesNotExist:
        pass

    display_messages_per_candidate = False
    force_retrieve = False
    num_candidates_reviewed = 0
    num_with_vote_smart_ids = 0
    num_candidates_just_retrieved = 0

    num_with_vote_smart_photos = 0
    num_candidate_photos_just_retrieved = 0

    message = "About to loop through all of the candidates in this election and retrieve photos."
    print_to_log(logger, exception_message_optional=message)

    # Loop through all of the candidates in this election
    for we_vote_candidate in candidate_list:
        num_candidates_reviewed += 1
        retrieve_candidate_results = retrieve_candidate_photos(we_vote_candidate, force_retrieve)
        if retrieve_candidate_results['vote_smart_candidate_exists']:
            num_with_vote_smart_ids += 1
        if retrieve_candidate_results['vote_smart_candidate_just_retrieved']:
            num_candidates_just_retrieved += 1

        if retrieve_candidate_results['vote_smart_candidate_photo_exists']:
            num_with_vote_smart_photos += 1
        if retrieve_candidate_results['vote_smart_candidate_photo_just_retrieved']:
            num_candidate_photos_just_retrieved += 1

        if retrieve_candidate_results['status'] and display_messages_per_candidate:
            messages.add_message(request, messages.INFO, retrieve_candidate_results['status'])

    message = "Google Civic Election ID: {election_id}, " \
              "{num_candidates_reviewed} candidates reviewed, " \
              "{num_with_vote_smart_ids} with Vote Smart Ids, " \
              "{num_candidates_just_retrieved} candidates just retrieved, " \
              "{num_with_vote_smart_photos} with Vote Smart Photos, and " \
              "{num_candidate_photos_just_retrieved} photos just retrieved.". \
        format(election_id=google_civic_election_id,
               num_candidates_reviewed=num_candidates_reviewed,
               num_with_vote_smart_ids=num_with_vote_smart_ids,
               num_candidates_just_retrieved=num_candidates_just_retrieved,
               num_with_vote_smart_photos=num_with_vote_smart_photos,
               num_candidate_photos_just_retrieved=num_candidate_photos_just_retrieved)

    print_to_log(logger, exception_message_optional=message)
    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}".format(
        var=google_civic_election_id))


@login_required
def candidate_summary_view(request, candidate_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    candidate_id = convert_to_int(candidate_id)
    candidate_we_vote_id = ""
    google_civic_election_id = 0
    state_code = ""
    candidate_on_stage_found = False

    candidate_search = request.GET.get('candidate_search', "")

    candidate_on_stage = CandidateCampaign()
    candidate_manager = CandidateManager()
    try:
        candidate_on_stage = CandidateCampaign.objects.get(id=candidate_id)
        candidate_we_vote_id = candidate_on_stage.we_vote_id
        # DALE 2020-05-24 Do we really need google_civic_election_id?
        google_civic_election_id = candidate_manager.fetch_next_upcoming_election_id_for_candidate(candidate_we_vote_id)
        state_code = candidate_on_stage.state_code
        candidate_on_stage_found = True
    except CandidateCampaign.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_candidate_to_office_link_list(
        candidate_we_vote_id_list=[candidate_we_vote_id])
    candidate_to_office_link_list = results['candidate_to_office_link_list']

    if positive_value_exists(candidate_we_vote_id):
        position_list_manager = PositionListManager()

        bookmark_item_list_manager = BookmarkItemList()

        # Get positions counts
        candidate_on_stage.public_positions_count = \
            position_list_manager.fetch_public_positions_count_for_candidate(
                candidate_on_stage.id, candidate_on_stage.we_vote_id)
        candidate_on_stage.friends_positions_count = \
            position_list_manager.fetch_friends_only_positions_count_for_candidate(
                candidate_on_stage.id, candidate_on_stage.we_vote_id)
        # Bookmarks
        bookmark_results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_candidate(
            candidate_on_stage.we_vote_id)
        if bookmark_results['bookmark_item_list_found']:
            bookmark_item_list = bookmark_results['bookmark_item_list']
            candidate_bookmark_count = len(bookmark_item_list)
        else:
            candidate_bookmark_count = 0
        candidate_on_stage.bookmarks_count = candidate_bookmark_count

    candidate_search_results_list = []
    # candidate_list_manager = CandidateListManager()
    # results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
    #     google_civic_election_id_list=google_civic_election_id_list,
    #     limit_to_this_state_code=state_code)
    # if not positive_value_exists(results['success']):
    #     status += results['status']
    #     success = False
    # candidate_we_vote_id_list = results['candidate_we_vote_id_list']
    if positive_value_exists(candidate_search) and positive_value_exists(candidate_we_vote_id):
        candidate_query = CandidateCampaign.objects.all()
        # office_visiting_list_we_vote_ids = office_manager.fetch_office_visiting_list_we_vote_ids(
        #     host_google_civic_election_id_list=[google_civic_election_id])
        # candidate_query = candidate_query.filter(
        #     Q(google_civic_election_id=google_civic_election_id) |
        #     Q(contest_office_we_vote_id__in=office_visiting_list_we_vote_ids))
        # candidate_query = candidate_query.exclude(we_vote_id__iexact=candidate_we_vote_id)

        if positive_value_exists(state_code):
            candidate_query = candidate_query.filter(state_code__iexact=state_code)

        search_words = candidate_search.split()
        for one_word in search_words:
            filters = []  # Reset for each search word
            new_filter = Q(candidate_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(contest_office_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(ballotpedia_candidate_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(contest_office_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_candidate_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_candidate_name2__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_candidate_name3__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(twitter_name__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                candidate_query = candidate_query.filter(final_filters)

        candidate_search_results_list = list(candidate_query)
    elif candidate_on_stage_found:
        ignore_candidate_we_vote_id_list = []
        ignore_candidate_we_vote_id_list.append(candidate_on_stage.we_vote_id)
        results = find_duplicate_candidate(candidate_on_stage, ignore_candidate_we_vote_id_list)
        if results['candidate_merge_possibility_found']:
            candidate_search_results_list = results['candidate_list']

    # Working with We Vote Positions
    try:
        candidate_position_query = PositionEntered.objects.order_by('stance')
        # As of Aug 2018 we are no longer using PERCENT_RATING
        candidate_position_query = candidate_position_query.exclude(stance__iexact='PERCENT_RATING')
        candidate_position_query = candidate_position_query.filter(candidate_campaign_id=candidate_id)
        candidate_position_list = list(candidate_position_query)
        # if positive_value_exists(google_civic_election_id):
        #     organization_position_list = candidate_position_list.filter(
        #         google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        candidate_position_list = []

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'candidate':                        candidate_on_stage,
        'candidate_to_office_link_list':    candidate_to_office_link_list,
        'candidate_search_results_list':    candidate_search_results_list,
        'google_civic_election_id':         google_civic_election_id,
        'state_code':                       state_code,
        'candidate_position_list':          candidate_position_list,
    }
    return render(request, 'candidate/candidate_summary.html', template_values)


@login_required
def candidate_delete_process_view(request):
    """
    Delete this candidate
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(request.GET.get('candidate_id', 0))
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    # Retrieve this candidate
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    if positive_value_exists(candidate_id):
        try:
            candidate_query = CandidateCampaign.objects.filter(id=candidate_id)
            if len(candidate_query):
                candidate_on_stage = candidate_query[0]
                candidate_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find candidate -- exception.')

    if not candidate_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find candidate.')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    # Are there any positions attached to this candidate that should be moved to another
    # instance of this candidate?
    position_list_manager = PositionListManager()
    retrieve_public_positions = True  # The alternate is positions for friends-only
    position_list = position_list_manager.retrieve_all_positions_for_candidate(
        retrieve_public_positions, candidate_id)
    if positive_value_exists(len(position_list)):
        positions_found_for_this_candidate = True
    else:
        positions_found_for_this_candidate = False

    try:
        if not positions_found_for_this_candidate:
            # Delete the candidate
            candidate_on_stage.delete()
            messages.add_message(request, messages.INFO, 'CandidateCampaign deleted.')
        else:
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'positions still attached to this candidate.')
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete candidate -- exception.')
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def compare_two_candidates_for_merge_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate1_we_vote_id = request.GET.get('candidate1_we_vote_id', 0)
    candidate2_we_vote_id = request.GET.get('candidate2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_manager = CandidateManager()
    candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate1_we_vote_id)
    if not candidate_results['candidate_found']:
        messages.add_message(request, messages.ERROR, "Candidate1 not found.")
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    candidate_option1_for_template = candidate_results['candidate']

    candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate2_we_vote_id)
    if not candidate_results['candidate_found']:
        messages.add_message(request, messages.ERROR, "Candidate2 not found.")
        return HttpResponseRedirect(reverse('candidate:candidate_summary', args=(candidate_option1_for_template.id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    candidate_option2_for_template = candidate_results['candidate']

    candidate_merge_conflict_values = figure_out_candidate_conflict_values(
        candidate_option1_for_template, candidate_option2_for_template)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_candidate_merge_form(request, candidate_option1_for_template,
                                       candidate_option2_for_template,
                                       candidate_merge_conflict_values,
                                       remove_duplicate_process)
