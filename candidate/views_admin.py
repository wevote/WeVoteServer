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
from django.utils.timezone import localtime
import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import BallotReturnedListManager
from bookmark.models import BookmarkItemList
from config.base import get_environment_variable
from election.controllers import retrieve_election_id_list_by_year_list, retrieve_upcoming_election_id_list
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
from wevote_functions.functions import convert_date_to_date_as_integer, convert_to_int, \
    convert_we_vote_date_string_to_date_as_integer, \
    extract_instagram_handle_from_text_string, \
    extract_twitter_handle_from_text_string, list_intersection, \
    positive_value_exists, STATE_CODE_MAP, display_full_name_with_correct_capitalization
from wevote_settings.constants import ELECTION_YEARS_AVAILABLE
from wevote_settings.models import RemoteRequestHistory, \
    RETRIEVE_POSSIBLE_GOOGLE_LINKS, RETRIEVE_POSSIBLE_TWITTER_HANDLES
from .controllers import candidates_import_from_master_server, candidates_import_from_sample_file, \
    candidate_politician_match, fetch_duplicate_candidate_count, figure_out_candidate_conflict_values, \
    find_duplicate_candidate, \
    merge_if_duplicate_candidates, merge_these_two_candidates, \
    retrieve_candidate_photos, retrieve_next_or_most_recent_office_for_candidate, \
    save_google_search_link_to_candidate_table, save_image_to_candidate_table
from .models import CandidateCampaign, CandidateListManager, CandidateManager, CandidateToOfficeLink, \
    CANDIDATE_UNIQUE_IDENTIFIERS, PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_UPLOADED, PROFILE_IMAGE_TYPE_VOTE_USA


CANDIDATES_SYNC_URL = get_environment_variable("CANDIDATES_SYNC_URL")  # candidatesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")

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

            new_filter = Q(candidate_twitter_handle2__icontains=candidate_search)
            filters.append(new_filter)

            new_filter = Q(candidate_twitter_handle3__icontains=candidate_search)
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
            'candidate_is_incumbent',
            'candidate_is_top_ticket',
            'candidate_name',
            'candidate_participation_status',
            'candidate_phone',
            'candidate_twitter_handle',
            'candidate_twitter_handle2',
            'candidate_twitter_handle3',
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
            'instagram_followers_count',
            'instagram_handle',
            'is_battleground_race',
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
    find_candidates_linked_to_multiple_offices = \
        positive_value_exists(request.GET.get('find_candidates_linked_to_multiple_offices', 0))
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = positive_value_exists(request.GET.get('hide_candidate_tools', 0))
    hide_candidates_with_photos = \
        positive_value_exists(request.GET.get('hide_candidates_with_photos', False))
    migrate_to_candidate_link = positive_value_exists(request.GET.get('migrate_to_candidate_link', False))
    page = convert_to_int(request.GET.get('page', 0))
    page = page if positive_value_exists(page) else 0  # Prevent negative pages
    # run_scripts = positive_value_exists(request.GET.get('run_scripts', False))
    run_scripts = True
    show_all = positive_value_exists(request.GET.get('show_all', False))
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    show_candidates_without_twitter = positive_value_exists(request.GET.get('show_candidates_without_twitter', False))
    show_candidates_with_best_twitter_options = \
        positive_value_exists(request.GET.get('show_candidates_with_best_twitter_options', False))
    show_candidates_with_twitter_options = \
        positive_value_exists(request.GET.get('show_candidates_with_twitter_options', False))
    show_election_statistics = positive_value_exists(request.GET.get('show_election_statistics', False))
    show_marquee_or_battleground = positive_value_exists(request.GET.get('show_marquee_or_battleground', False))
    show_this_year_of_candidates = convert_to_int(request.GET.get('show_this_year_of_candidates', 0))

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
    candidate_list_manager = CandidateListManager()

    candidate_we_vote_id_list = []
    if positive_value_exists(google_civic_election_id):
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=[google_civic_election_id])
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    # If we are looking at one specific election, find all the candidates under that election and make sure each
    #  candidate entry has a value for candidate_ultimate_election_date. Note this won't update candidates
    #  who have the general election as their ultimate_election_date, if they lost in the primary. That will require
    #  an update to this script.
    populate_candidate_ultimate_election_date = True
    number_to_populate = 10  # Normally we can process 10000 at a time
    if populate_candidate_ultimate_election_date and positive_value_exists(google_civic_election_id) and run_scripts:
        # We require google_civic_election_id just so we can limit the scope of this update
        populate_candidate_ultimate_election_date_status = ''
        # Find all candidates in this election
        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            google_civic_election_id_list=[google_civic_election_id],
            read_only=True)
        candidate_to_office_link_list = results['candidate_to_office_link_list']
        candidates_to_update_we_vote_id_list = []
        for candidate_to_office_link in candidate_to_office_link_list:
            if candidate_to_office_link.candidate_we_vote_id not in candidates_to_update_we_vote_id_list:
                candidates_to_update_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)

        # Now get all candidates we want to update, with a single query
        candidate_query = CandidateCampaign.objects.all()
        candidate_query = candidate_query.filter(we_vote_id__in=candidates_to_update_we_vote_id_list)
        # For now, restrict to those who don't have candidate_ultimate_election_date. In the future, we could remove
        #  this to refresh the candidate_ultimate_election_date data for all candidates.
        candidate_query = candidate_query.filter(
            Q(candidate_ultimate_election_date=0) | Q(candidate_ultimate_election_date__isnull=True))
        candidate_ultimate_count = candidate_query.count()
        if positive_value_exists(candidate_ultimate_count):
            populate_candidate_ultimate_election_date_status += \
                "SCRIPT: {entries_to_process} entries to process (populate_candidate_ultimate_election_date) " \
                "".format(entries_to_process=candidate_ultimate_count) + " "
        # Now process
        candidate_bulk_update_list = []
        candidate_list = candidate_query[:number_to_populate]
        candidates_updated = 0
        candidates_not_updated = 0
        elections_dict = {}
        from candidate.controllers import augment_candidate_with_ultimate_election_date
        for one_candidate in candidate_list:
            results = augment_candidate_with_ultimate_election_date(
                candidate=one_candidate,
                elections_dict=elections_dict)
            if results['success']:
                elections_dict = results['elections_dict']
            if results['values_changed']:
                candidate_bulk_update_list.append(results['candidate'])
                candidates_updated += 1
            else:
                candidates_not_updated += 1
        if len(candidate_bulk_update_list) > 0:
            try:
                CandidateCampaign.objects.bulk_update(
                    candidate_bulk_update_list,
                    ['candidate_ultimate_election_date',
                     'candidate_year'])
            except Exception as e:
                messages.add_message(request, messages.ERROR, "FAILED_BULK_UPDATE: " + str(e))

        if positive_value_exists(candidates_updated):
            populate_candidate_ultimate_election_date_status += \
                "candidates_updated: " + str(candidates_updated) + " "
        if positive_value_exists(candidates_not_updated):
            populate_candidate_ultimate_election_date_status += \
                "candidates_not_updated: " + str(candidates_updated) + " "
        if positive_value_exists(populate_candidate_ultimate_election_date_status):
            messages.add_message(request, messages.INFO, populate_candidate_ultimate_election_date_status)

    # Update candidates who currently don't have seo_friendly_path, if there is seo_friendly_path
    #  in linked politician
    number_to_update = 1000
    seo_friendly_path_updates = True
    if seo_friendly_path_updates and run_scripts:
        seo_friendly_path_updates_status = ""
        seo_update_query = CandidateCampaign.objects.all()
        seo_update_query = seo_update_query.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id="")
        )
        seo_update_query = seo_update_query.filter(
            Q(seo_friendly_path__isnull=True) |
            Q(seo_friendly_path="")
        )
        if positive_value_exists(google_civic_election_id):
            seo_update_query = seo_update_query.filter(we_vote_id__in=candidate_we_vote_id_list)
        # After initial updates to all candidates, include in the search logic to find candidates with
        # seo_friendly_path_date_last_updated older than Politician.seo_friendly_path_date_last_updated
        if positive_value_exists(state_code):
            seo_update_query = seo_update_query.filter(state_code__iexact=state_code)
        total_to_convert = seo_update_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        seo_update_query = seo_update_query.order_by('-id')
        candidate_list = list(seo_update_query[:number_to_update])
        politician_we_vote_id_list = []
        # Retrieve all relevant politicians in a single query
        for one_candidate in candidate_list:
            politician_we_vote_id_list.append(one_candidate.politician_we_vote_id)
        politician_manager = PoliticianManager()
        politician_list = []
        if len(politician_we_vote_id_list) > 0:
            politician_results = politician_manager.retrieve_politician_list(
                politician_we_vote_id_list=politician_we_vote_id_list)
            politician_list = politician_results['politician_list']
        politician_dict_list = {}
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician
        timezone = pytz.timezone("America/Los_Angeles")
        datetime_now = timezone.localize(datetime.now())
        seo_friendly_path_missing = 0
        update_list = []
        updates_needed = False
        updates_made = 0
        for one_candidate in candidate_list:
            one_politician = politician_dict_list.get(one_candidate.politician_we_vote_id)
            if positive_value_exists(one_politician.seo_friendly_path):
                one_candidate.seo_friendly_path = one_politician.seo_friendly_path
                one_candidate.seo_friendly_path_date_last_updated = datetime_now
                update_list.append(one_candidate)
                updates_needed = True
                updates_made += 1
            else:
                seo_friendly_path_missing += 1
        if positive_value_exists(seo_friendly_path_missing):
            seo_friendly_path_updates_status += \
                "{seo_friendly_path_missing:,} missing seo_friendly_path (not found in Politician). " \
                "".format(seo_friendly_path_missing=seo_friendly_path_missing)
        if updates_needed:
            CandidateCampaign.objects.bulk_update(
                update_list, ['seo_friendly_path', 'seo_friendly_path_date_last_updated'])
            seo_friendly_path_updates_status += \
                "{updates_made:,} candidates updated with new seo_friendly_path. " \
                "{total_to_convert_after:,} remaining." \
                "".format(total_to_convert_after=total_to_convert_after, updates_made=updates_made)
        if positive_value_exists(seo_friendly_path_updates_status):
            seo_friendly_path_updates_status += "(UPDATE_SCRIPT) "
            messages.add_message(request, messages.INFO, seo_friendly_path_updates_status)

    # Update candidates who currently don't have linked_campaignx_we_vote_id, with value from linked politician
    number_to_update = 1000
    campaignx_we_vote_id_updates = True
    if campaignx_we_vote_id_updates and run_scripts:
        campaignx_we_vote_id_updates_status = ""
        # After initial updates to all candidates, include in the search logic to find candidates with
        # linked_campaignx_we_vote_id_date_last_updated older than:
        # Politician.linked_campaignx_we_vote_id_date_last_updated
        update_query = CandidateCampaign.objects.all()
        update_query = update_query.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id="")
        )
        update_query = update_query.filter(
            Q(linked_campaignx_we_vote_id__isnull=True) |
            Q(linked_campaignx_we_vote_id="")
        )
        # After initial updates to all candidates, include in the search logic to find candidates with
        # linked_campaignx_we_vote_id_date_last_updated older than
        # Politician.linked_campaignx_we_vote_id_date_last_updated
        if positive_value_exists(google_civic_election_id):
            update_query = update_query.filter(we_vote_id__in=candidate_we_vote_id_list)
        if positive_value_exists(state_code):
            update_query = update_query.filter(state_code__iexact=state_code)
        total_to_convert = update_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        update_query = update_query.order_by('-id')
        candidate_list = list(update_query[:number_to_update])
        politician_we_vote_id_list = []
        # Retrieve all relevant politicians in a single query
        for one_candidate in candidate_list:
            politician_we_vote_id_list.append(one_candidate.politician_we_vote_id)
        politician_manager = PoliticianManager()
        politician_list = []
        if len(politician_we_vote_id_list) > 0:
            politician_results = politician_manager.retrieve_politician_list(
                politician_we_vote_id_list=politician_we_vote_id_list)
            politician_list = politician_results['politician_list']
        politician_dict_list = {}
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician
        timezone = pytz.timezone("America/Los_Angeles")
        datetime_now = timezone.localize(datetime.now())
        linked_campaignx_we_vote_id_missing = 0
        update_list = []
        updates_needed = False
        updates_made = 0
        for one_candidate in candidate_list:
            one_politician = politician_dict_list.get(one_candidate.politician_we_vote_id)
            if positive_value_exists(one_politician.linked_campaignx_we_vote_id):
                one_candidate.linked_campaignx_we_vote_id = one_politician.linked_campaignx_we_vote_id
                one_candidate.linked_campaignx_we_vote_id_date_last_updated = datetime_now
                update_list.append(one_candidate)
                updates_needed = True
                updates_made += 1
            else:
                linked_campaignx_we_vote_id_missing += 1
        if positive_value_exists(linked_campaignx_we_vote_id_missing):
            campaignx_we_vote_id_updates_status += \
                "{linked_campaignx_we_vote_id_missing:,} missing linked_campaignx_we_vote_id." \
                "".format(linked_campaignx_we_vote_id_missing=linked_campaignx_we_vote_id_missing)
        if updates_needed:
            try:
                CandidateCampaign.objects.bulk_update(
                    update_list, ['linked_campaignx_we_vote_id', 'linked_campaignx_we_vote_id_date_last_updated'])
                campaignx_we_vote_id_updates_status += \
                    "{updates_made:,} candidates updated with new linked_campaignx_we_vote_id. " \
                    "{total_to_convert_after:,} remaining." \
                    "".format(
                        total_to_convert_after=total_to_convert_after,
                        updates_made=updates_made)
            except Exception as e:
                campaignx_we_vote_id_updates_status += \
                    "{updates_made:,} candidates NOT updated with new linked_campaignx_we_vote_id. " \
                    "{total_to_convert_after:,} remaining. ERROR: {error}" \
                    "".format(
                         error=str(e),
                         total_to_convert_after=total_to_convert_after,
                         updates_made=updates_made)
        if positive_value_exists(campaignx_we_vote_id_updates_status):
            campaignx_we_vote_id_updates_status = \
                "SCRIPT campaignx_we_vote_id_updates: " + campaignx_we_vote_id_updates_status + " "
            messages.add_message(request, messages.INFO, campaignx_we_vote_id_updates_status)

    google_civic_election_id_list_generated = False
    show_this_year_of_candidates_restriction = False
    if positive_value_exists(google_civic_election_id):
        google_civic_election_id_list = [convert_to_int(google_civic_election_id)]
        google_civic_election_id_list_generated = True
    elif positive_value_exists(show_this_year_of_candidates):
        google_civic_election_id_list = retrieve_election_id_list_by_year_list([show_this_year_of_candidates])
        show_this_year_of_candidates_restriction = True
    elif positive_value_exists(show_all_elections):
        google_civic_election_id_list = []
    else:
        # Limit to just upcoming elections
        google_civic_election_id_list_generated = True
        google_civic_election_id_list = retrieve_upcoming_election_id_list()

    candidate_we_vote_id_list = []
    if show_this_year_of_candidates_restriction:
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_year_list(
            year_list=[show_this_year_of_candidates],
            limit_to_this_state_code=state_code)
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']
    elif google_civic_election_id_list_generated:
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
    # show_this_year_of_candidates_restriction
    if (google_civic_election_id_list_generated or show_this_year_of_candidates_restriction) \
            and show_marquee_or_battleground:
        filtered_candidate_we_vote_id_list = list_intersection(
            candidate_we_vote_id_list, battleground_candidate_we_vote_id_list)
    elif google_civic_election_id_list_generated or show_this_year_of_candidates_restriction:
        filtered_candidate_we_vote_id_list = candidate_we_vote_id_list
    elif show_marquee_or_battleground:
        filtered_candidate_we_vote_id_list = battleground_candidate_we_vote_id_list

    # Now retrieve the candidate_list from the filtered_candidate_we_vote_id_list
    try:
        candidate_query = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id_list_generated) \
                or positive_value_exists(show_marquee_or_battleground) \
                or positive_value_exists(show_this_year_of_candidates_restriction):
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

                new_filter = Q(candidate_twitter_handle2__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(candidate_twitter_handle3__icontains=one_word)
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

                new_filter = Q(linked_campaignx_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(politician_we_vote_id__iexact=one_word)
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
                twitter_query = twitter_query.values_list('candidate_campaign_we_vote_id', flat=True).distinct()
                twitter_list = list(twitter_query)
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
                twitter_query = twitter_query.values_list('candidate_campaign_we_vote_id', flat=True).distinct()
                twitter_possibility_list = list(twitter_query)
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
        if positive_value_exists(show_all) or positive_value_exists(find_candidates_linked_to_multiple_offices):
            candidate_list = list(candidate_query)
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
        pass

    candidates_linked_to_multiple_offices = 0
    if positive_value_exists(google_civic_election_id) and \
            positive_value_exists(find_candidates_linked_to_multiple_offices):
        # Only include candidates who are linked to two offices in the same election
        results = candidate_list_manager.retrieve_candidate_to_office_link_duplicate_candidate_we_vote_ids(
            google_civic_election_id=google_civic_election_id,
            state_code=state_code,
        )
        if results['success']:
            candidate_we_vote_id_list = results['candidate_we_vote_id_list']
            modified_candidate_list = []
            for one_candidate in candidate_list:
                if one_candidate.we_vote_id in candidate_we_vote_id_list:
                    modified_candidate_list.append(one_candidate)
            candidate_list = modified_candidate_list
        candidates_linked_to_multiple_offices = len(candidate_list)

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
    status_print_list += "{candidate_list_count:,} candidates found." \
                         "".format(candidate_list_count=candidate_list_count)

    if find_candidates_linked_to_multiple_offices:
        status_print_list += "candidates_linked_to_multiple_offices: " + str(candidates_linked_to_multiple_offices) + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    # Provide this election to the template, so we can show election statistics
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
            if positive_value_exists(candidate.instagram_handle):
                url = extract_instagram_handle_from_text_string(candidate.instagram_handle)
                if not url.startswith('https://'):
                    url = ('https://www.instagram.com/' + candidate.instagram_handle).strip().replace('@', '')
                candidate.instagram_url = url
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

    if positive_value_exists(google_civic_election_id) and positive_value_exists(state_code):
        from import_export_vote_usa.controllers import VOTE_USA_API_KEY, VOTE_USA_CANDIDATE_QUERY_URL
        vote_usa_candidates_for_this_state = \
            VOTE_USA_CANDIDATE_QUERY_URL + \
            "?accessKey={access_key}&electionDay={election_day}&state={state_code}".format(
                access_key=VOTE_USA_API_KEY,
                election_day='2022-11-08',
                state_code=state_code,
            )
    else:
        vote_usa_candidates_for_this_state = ''

    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
    template_values = {
        'candidate_count_start':                    candidate_count_start,
        'candidate_list':                           candidate_list,
        'candidate_search':                         candidate_search,
        'current_page_number':                      page,
        'current_page_minus_candidate_tools_url':   current_page_minus_candidate_tools_url,
        'election':                                 election,
        'election_list':                            election_list,
        'election_years_available':                 ELECTION_YEARS_AVAILABLE,
        'facebook_urls_without_picture_urls':       facebook_urls_without_picture_urls,
        'find_candidates_linked_to_multiple_offices':   find_candidates_linked_to_multiple_offices,
        'google_civic_election_id':                 google_civic_election_id,
        'hide_candidate_tools':                     hide_candidate_tools,
        'hide_candidates_with_photos':              hide_candidates_with_photos,
        'hide_pagination':                          hide_pagination,
        'messages_on_stage':                        messages_on_stage,
        'next_page_url':                            next_page_url,
        'previous_page_url':                        previous_page_url,
        'review_mode':                              review_mode,
        'show_all_elections':                       show_all_elections,
        'show_candidates_with_best_twitter_options':    show_candidates_with_best_twitter_options,
        'show_candidates_with_twitter_options':     show_candidates_with_twitter_options,
        'show_candidates_without_twitter':          show_candidates_without_twitter,
        'show_election_statistics':                 show_election_statistics,
        'show_marquee_or_battleground':             show_marquee_or_battleground,
        'show_this_year_of_candidates':             show_this_year_of_candidates,
        'state_code':                               state_code,
        'state_list':                               sorted_state_list,
        'total_twitter_handles':                    total_twitter_handles,
        'vote_usa_candidates_for_this_state':       vote_usa_candidates_for_this_state,
        'web_app_root_url':                         web_app_root_url,
    }
    return render(request, 'candidate/candidate_list.html', template_values)


@login_required
def candidate_new_search_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    contest_office_id = request.GET.get('contest_office_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    # no_office: We want to be able to add candidates before we have the upcoming election, and without knowing
    #  the office information. This is useful for candidate campaigns that start 2 years before the election.
    no_office = positive_value_exists(request.GET.get('no_office', False))
    state_code = request.GET.get('state_code', "")

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

    candidate_list = []
    contest_office_list = []
    office_name = ''
    state_code_from_election = ''
    state_code_from_office = ''
    if google_civic_election_id:
        # These are the Offices already entered for this election
        try:
            office_queryset = ContestOffice.objects.order_by('office_name')
            office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
            contest_office_list = list(office_queryset)

        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            contest_office_list = []

    if positive_value_exists(contest_office_id):
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

        # It's helpful to see existing candidates when entering a new candidate
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
    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
    template_values = {
        'messages_on_stage':                messages_on_stage,
        'office_list':                      contest_office_list,
        'contest_office_id':                contest_office_id,  # Pass in separately for the template to work
        'google_civic_election_id':         google_civic_election_id,
        'candidate_list':                   candidate_list,
        'state_code_from_election':         state_code_from_election,
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
        'web_app_root_url':                 web_app_root_url,
    }
    return render(request, 'candidate/candidate_new_search.html', template_values)


@login_required
def candidate_new_search_process_view(request):
    """
    Search to see if this candidate already exists before adding
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()
    politician_manager = PoliticianManager()

    status = ""

    candidate_id = convert_to_int(request.POST.get('candidate_id', 0))
    if not positive_value_exists(candidate_id):
        candidate_id = convert_to_int(request.GET.get('candidate_id', 0))
    candidate_name = request.POST.get('candidate_name', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    candidate_twitter_handle = request.POST.get('candidate_twitter_handle', False)
    if positive_value_exists(candidate_twitter_handle):
        candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle)
    candidate_url = request.POST.get('candidate_url', '')
    candidate_contact_form_url = request.POST.get('candidate_contact_form_url', False)
    facebook_url = request.POST.get('facebook_url', False)
    instagram_handle = request.POST.get('instagram_handle', False)
    if positive_value_exists(instagram_handle):
        instagram_handle = extract_instagram_handle_from_text_string(instagram_handle)
    candidate_email = request.POST.get('candidate_email', False)
    contest_office_id = request.POST.get('contest_office_id', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)
    state_code = request.POST.get('state_code', '')
    vote_usa_politician_id = request.POST.get('vote_usa_politician_id', False)

    # For starting "Create new candidate" process
    candidate_name_search = request.GET.get('candidate_name_search', False)
    if not positive_value_exists(candidate_name):
        candidate_name = candidate_name_search
    politician_we_vote_id_for_start = request.GET.get('politician_we_vote_id_for_start', False)
    if not positive_value_exists(politician_we_vote_id):
        politician_we_vote_id = politician_we_vote_id_for_start

    politician_list = []
    # If here, we specifically want to see if a politician exists, given the information submitted
    from wevote_functions.functions import add_to_list_if_positive_value_exists
    facebook_url_list = []
    facebook_url_list = add_to_list_if_positive_value_exists(facebook_url, facebook_url_list)
    full_name_list = []
    full_name_list = add_to_list_if_positive_value_exists(candidate_name, full_name_list)
    twitter_handle_list = []
    twitter_handle_list = add_to_list_if_positive_value_exists(candidate_twitter_handle, twitter_handle_list)
    match_results = politician_manager.retrieve_all_politicians_that_might_match_similar_object(
        facebook_url_list=facebook_url_list,
        full_name_list=full_name_list,
        twitter_handle_list=twitter_handle_list,
        return_close_matches=True,
        state_code=state_code,
        vote_usa_politician_id=vote_usa_politician_id)
    # TODO This is still a work in progress
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
        politician_list = []
        politician_list.append(matching_politician)
    elif match_results['politician_list_found']:
        politician_list = match_results['politician_list']
    else:
        messages.add_message(request, messages.INFO, 'No politician found. Please make sure you have entered '
                                                     '1) Candidate Name, '
                                                     '2) Twitter Handle, or '
                                                     '3) TBD')

    # Return all existing related candidates. Make sure the candidate we want to create doesn't already exist.
    candidate_list = []
    if positive_value_exists(candidate_name_search) or positive_value_exists(politician_we_vote_id):
        if positive_value_exists(politician_we_vote_id):
            politician_we_vote_id_list = [politician_we_vote_id]
            candidate_results = candidate_list_manager.retrieve_candidate_list(
                politician_we_vote_id_list=politician_we_vote_id_list)
            if candidate_results['candidate_list_found']:
                candidate_list = candidate_results['candidate_list']

    # ##################################
    # Find Candidates that *might* be "children" of this politician
    candidate_we_vote_id_list = []
    if positive_value_exists(politician_list) and len(politician_list) > 0:
        from politician.controllers import find_candidates_to_link_to_this_politician
        related_candidate_list = find_candidates_to_link_to_this_politician(politician=politician_list[0])
        for candidate in candidate_list:
            candidate_we_vote_id_list.append(candidate.we_vote_id)
        for candidate in related_candidate_list:
            if candidate.we_vote_id not in candidate_we_vote_id_list:
                candidate_we_vote_id_list.append(candidate.we_vote_id)
                candidate_list.append(candidate)

    # Make sure candidate_list entries have office and election information
    candidate_list_modified = []
    for candidate in candidate_list:
        retrieve_candidate_to_office_link = False
        if not positive_value_exists(candidate.contest_office_we_vote_id):
            retrieve_candidate_to_office_link = True
        if not positive_value_exists(candidate.google_civic_election_id):
            retrieve_candidate_to_office_link = True
        if retrieve_candidate_to_office_link:
            results = candidate_list_manager.retrieve_candidate_to_office_link_list(
                    candidate_we_vote_id_list=[candidate.we_vote_id])
            if results['candidate_to_office_link_list'] and len(results['candidate_to_office_link_list']) > 0:
                candidate_to_office_link = results['candidate_to_office_link_list'][0]
                if positive_value_exists(candidate_to_office_link.contest_office_we_vote_id) and \
                        positive_value_exists(candidate_to_office_link.google_civic_election_id):
                    candidate.contest_office_we_vote_id = candidate_to_office_link.contest_office_we_vote_id
                    candidate.google_civic_election_id = candidate_to_office_link.google_civic_election_id
        candidate_list_modified.append(candidate)

    candidate_list = candidate_list_modified

    def sort_by_election_year(candidate):
        if candidate and hasattr(candidate, 'candidate_year'):
            if candidate.candidate_year:
                return convert_to_int(candidate.candidate_year)
            else:
                return 0
        else:
            return 0

    if len(candidate_list) > 0:
        candidate_list.sort(key=sort_by_election_year, reverse=True)

    # If ready to start full process
    ready = False
    if ready:
        url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                        "&candidate_name=" + str(candidate_name) + \
                        "&state_code=" + str(state_code) + \
                        "&contest_office_id=" + str(contest_office_id) + \
                        "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                        "&candidate_url=" + str(candidate_url) + \
                        "&candidate_contact_form_url=" + str(candidate_contact_form_url) + \
                        "&facebook_url=" + str(facebook_url) + \
                        "&instagram_handle=" + str(instagram_handle) + \
                        "&candidate_email=" + str(candidate_email) + \
                        "&politician_we_vote_id=" + str(politician_we_vote_id)
        if positive_value_exists(candidate_id):
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                        url_variables)
        else:
            return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) +
                                        url_variables)

    # url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
    #                 "&candidate_name=" + str(candidate_name) + \
    #                 "&state_code=" + str(state_code) + \
    #                 "&contest_office_id=" + str(contest_office_id) + \
    #                 "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
    #                 "&candidate_url=" + str(candidate_url) + \
    #                 "&candidate_contact_form_url=" + str(candidate_contact_form_url) + \
    #                 "&facebook_url=" + str(facebook_url) + \
    #                 "&instagram_handle=" + str(instagram_handle) + \
    #                 "&candidate_email=" + str(candidate_email) + \
    #                 "&politician_we_vote_id=" + str(politician_we_vote_id)
    #
    # return HttpResponseRedirect(reverse('candidate:candidate_new', args=(candidate_id,)) +
    #                             url_variables)
    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':            messages_on_stage,
        'contest_office_id':            contest_office_id,  # Pass in separately for the template to work
        'google_civic_election_id':     google_civic_election_id,
        # Incoming variables, not saved yet
        'candidate_count_start':        0,
        'candidate_list':               candidate_list,
        'candidate_name':               candidate_name,
        'candidate_twitter_handle':     candidate_twitter_handle,
        'candidate_url':                candidate_url,
        'candidate_contact_form_url':   candidate_contact_form_url,
        'politician_list':              politician_list,
        'politician_we_vote_id':        politician_we_vote_id,
        'state_code':                   state_code,
    }
    return render(request, 'candidate/candidate_new_search.html', template_values)


@login_required
def candidate_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    contest_office_id = request.GET.get('contest_office_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    # no_office: We want to be able to add candidates before we have the upcoming election, and without knowing
    #  the office information. This is useful for candidate campaigns that start 2 years before the election.
    no_office = positive_value_exists(request.GET.get('no_office', False))
    state_code = request.GET.get('state_code', "")

    if not no_office and not positive_value_exists(contest_office_id):
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

    candidate_list = []
    contest_office_list = []
    office_name = ''
    state_code_from_election = ''
    state_code_from_office = ''
    if not no_office:
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

        # It's helpful to see existing candidates when entering a new candidate
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
        'messages_on_stage':                messages_on_stage,
        'office_list':                      contest_office_list,
        'contest_office_id':                contest_office_id,  # Pass in separately for the template to work
        'google_civic_election_id':         google_civic_election_id,
        'candidate_list':                   candidate_list,
        'state_code_from_election':         state_code_from_election,
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
    candidate_twitter_handle2 = request.GET.get('candidate_twitter_handle2', False)
    candidate_twitter_handle3 = request.GET.get('candidate_twitter_handle3', False)
    candidate_url = request.GET.get('candidate_url', False)
    candidate_contact_form_url = request.GET.get('candidate_contact_form_url', False)
    facebook_url = request.GET.get('facebook_url', False)
    instagram_handle = request.GET.get('instagram_handle', False)
    if positive_value_exists(instagram_handle):
        instagram_handle = extract_instagram_handle_from_text_string(instagram_handle)
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

    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
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
            'candidate_twitter_handle2':        candidate_twitter_handle2,
            'candidate_twitter_handle3':        candidate_twitter_handle3,
            'candidate_url':                    candidate_url,
            'candidate_contact_form_url':       candidate_contact_form_url,
            'facebook_url':                     facebook_url,
            'instagram_handle':                 instagram_handle,
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
            'web_app_root_url':                 web_app_root_url,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            # Incoming variables
            'vote_smart_id':        vote_smart_id,
            'web_app_root_url':     web_app_root_url,
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
            start, count, read_only=True)
    else:
        politician_manager = PoliticianManager()
        list_of_people_from_db, number_of_rows = politician_manager.retrieve_politicians_with_misformatted_names(
            start, count, read_only=True)

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
    candidate_ultimate_election_date = False
    candidate_year = False

    status = ""

    ballot_guide_official_statement = request.POST.get('ballot_guide_official_statement', False)
    ballotpedia_candidate_id = request.POST.get('ballotpedia_candidate_id', False)
    ballotpedia_candidate_name = request.POST.get('ballotpedia_candidate_name', False)
    ballotpedia_candidate_url = request.POST.get('ballotpedia_candidate_url', False)
    ballotpedia_candidate_summary = request.POST.get('ballotpedia_candidate_summary', False)
    ballotpedia_office_id = request.POST.get('ballotpedia_office_id', False)
    ballotpedia_person_id = request.POST.get('ballotpedia_person_id', False)
    ballotpedia_race_id = request.POST.get('ballotpedia_race_id', False)
    candidate_id = convert_to_int(request.POST.get('candidate_id', 0))
    if not positive_value_exists(candidate_id):
        candidate_id = convert_to_int(request.GET.get('candidate_id', 0))
    candidate_name = request.POST.get('candidate_name', False)
    candidate_url = request.POST.get('candidate_url', False)
    candidate_contact_form_url = request.POST.get('candidate_contact_form_url', False)
    candidate_email = request.POST.get('candidate_email', False)
    candidate_phone = request.POST.get('candidate_phone', False)
    candidate_twitter_handle = request.POST.get('candidate_twitter_handle', False)
    if positive_value_exists(candidate_twitter_handle):
        candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle)
    candidate_twitter_handle2 = request.POST.get('candidate_twitter_handle2', False)
    if positive_value_exists(candidate_twitter_handle2):
        candidate_twitter_handle2 = extract_twitter_handle_from_text_string(candidate_twitter_handle2)
    candidate_twitter_handle3 = request.POST.get('candidate_twitter_handle3', False)
    if positive_value_exists(candidate_twitter_handle3):
        candidate_twitter_handle3 = extract_twitter_handle_from_text_string(candidate_twitter_handle3)
    contest_office_id = request.POST.get('contest_office_id', False)
    do_not_display_on_ballot = positive_value_exists(request.POST.get('do_not_display_on_ballot', False))
    facebook_url = request.POST.get('facebook_url', False)
    google_civic_candidate_name = request.POST.get('google_civic_candidate_name', False)
    google_civic_candidate_name2 = request.POST.get('google_civic_candidate_name2', False)
    google_civic_candidate_name3 = request.POST.get('google_civic_candidate_name3', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    google_search_image_file = request.POST.get('google_search_image_file', False)
    google_search_link = request.POST.get('google_search_link', False)
    hide_candidate_tools = request.POST.get('hide_candidate_tools', False)
    instagram_handle = request.POST.get('instagram_handle', False)
    if positive_value_exists(instagram_handle):
        instagram_handle = extract_instagram_handle_from_text_string(instagram_handle)
    linkedin_url = request.POST.get('linkedin_url', False)
    look_for_politician = request.POST.get('look_for_politician', False)  # If this comes in with value, don't save
    maplight_id = request.POST.get('maplight_id', False)
    page = convert_to_int(request.POST.get('page', 0))
    party = request.POST.get('party', False)
    photo_url_from_vote_usa = request.POST.get('photo_url_from_vote_usa', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)
    profile_image_type_currently_active = request.POST.get('profile_image_type_currently_active', False)
    redirect_to_candidate_list = positive_value_exists(request.POST.get('redirect_to_candidate_list', False))
    refresh_from_twitter = request.POST.get('refresh_from_twitter', False)
    reject_twitter_link_possibility_id = convert_to_int(request.POST.get('reject_twitter_link_possibility_id', 0))
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    select_for_marking_twitter_link_possibility_ids = request.POST.getlist('select_for_marking_checks[]')
    state_code = request.POST.get('state_code', False)
    twitter_handle_updates_failing = request.POST.get('twitter_handle_updates_failing', False)
    twitter_handle_updates_failing = positive_value_exists(twitter_handle_updates_failing)
    twitter_handle2_updates_failing = request.POST.get('twitter_handle2_updates_failing', False)
    twitter_handle2_updates_failing = positive_value_exists(twitter_handle2_updates_failing)
    twitter_url = request.POST.get('twitter_url', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    vote_usa_office_id = request.POST.get('vote_usa_office_id', False)
    vote_usa_politician_id = request.POST.get('vote_usa_politician_id', False)
    which_marking = request.POST.get('which_marking')
    wikipedia_url = request.POST.get('wikipedia_url', False)
    withdrawal_date = request.POST.get('withdrawal_date', False)
    withdrawn_from_election = positive_value_exists(request.POST.get('withdrawn_from_election', False))
    youtube_url = request.POST.get('youtube_url', False)

    url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                    "&ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                    "&candidate_contact_form_url=" + str(candidate_contact_form_url) + \
                    "&candidate_email=" + str(candidate_email) + \
                    "&candidate_name=" + str(candidate_name) + \
                    "&candidate_phone=" + str(candidate_phone) + \
                    "&candidate_twitter_handle=" + str(candidate_twitter_handle) + \
                    "&candidate_twitter_handle2=" + str(candidate_twitter_handle2) + \
                    "&candidate_twitter_handle3=" + str(candidate_twitter_handle3) + \
                    "&candidate_url=" + str(candidate_url) + \
                    "&contest_office_id=" + str(contest_office_id) + \
                    "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                    "&google_civic_candidate_name2=" + str(google_civic_candidate_name2) + \
                    "&google_civic_candidate_name3=" + str(google_civic_candidate_name3) + \
                    "&facebook_url=" + str(facebook_url) + \
                    "&instagram_handle=" + str(instagram_handle) + \
                    "&maplight_id=" + str(maplight_id) + \
                    "&party=" + str(party) + \
                    "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                    "&state_code=" + str(state_code) + \
                    "&vote_smart_id=" + str(vote_smart_id)

    # Note: A date is not required, but if provided it needs to be in a correct date format
    if positive_value_exists(withdrawn_from_election) and positive_value_exists(withdrawal_date):
        # If withdrawn_from_election is true AND we have an invalid withdrawal_date return with error
        res = re.match(r'([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))', withdrawal_date)
        if res is None:
            print('withdrawal_date is invalid: ' + withdrawal_date)
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
    election_manager = ElectionManager()
    office_manager = ContestOfficeManager()
    state_code_from_candidate = ''
    candidate_we_vote_id = ''
    if positive_value_exists(candidate_id):
        # We don't put this in a try/except block because we want the page to fail if there's an error
        candidate_query = CandidateCampaign.objects.filter(id=candidate_id)
        if len(candidate_query):
            candidate_on_stage = candidate_query[0]
            candidate_we_vote_id = candidate_on_stage.we_vote_id
            candidate_year = candidate_on_stage.candidate_year
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
    if not positive_value_exists(candidate_to_office_link_add_election):
        candidate_to_office_link_add_election = request.GET.get('candidate_to_office_link_add_election', False)
    candidate_to_office_link_add_state_code = request.POST.get('candidate_to_office_link_add_state_code', False)
    if not positive_value_exists(candidate_to_office_link_add_state_code):
        candidate_to_office_link_add_state_code = request.GET.get('candidate_to_office_link_add_state_code', False)
    candidate_to_office_link_add_office_we_vote_id = \
        request.POST.get('candidate_to_office_link_add_office_we_vote_id', False)
    if not positive_value_exists(candidate_to_office_link_add_office_we_vote_id):
        candidate_to_office_link_add_office_we_vote_id = \
            request.GET.get('candidate_to_office_link_add_office_we_vote_id', False)
    candidate_to_office_link_add_office_held_we_vote_id = \
        request.POST.get('candidate_to_office_link_add_office_held_we_vote_id', False)
    if not positive_value_exists(candidate_to_office_link_add_office_held_we_vote_id):
        candidate_to_office_link_add_office_held_we_vote_id = \
            request.GET.get('candidate_to_office_link_add_office_held_we_vote_id', False)

    if positive_value_exists(candidate_to_office_link_add_election) and \
            positive_value_exists(candidate_to_office_link_add_state_code) and \
            (positive_value_exists(candidate_to_office_link_add_office_we_vote_id) or
             positive_value_exists(candidate_to_office_link_add_office_held_we_vote_id)):
        candidate_to_office_link_add_election = candidate_to_office_link_add_election.strip()
        if positive_value_exists(candidate_to_office_link_add_office_we_vote_id):
            candidate_to_office_link_add_office_we_vote_id = candidate_to_office_link_add_office_we_vote_id.strip()
        if positive_value_exists(candidate_to_office_link_add_state_code):
            candidate_to_office_link_add_state_code = candidate_to_office_link_add_state_code.strip()
        if positive_value_exists(candidate_to_office_link_add_election) and \
                positive_value_exists(candidate_to_office_link_add_office_held_we_vote_id):
            # Does a ContestOffice for this upcoming election + OfficeHeld exist?
            results = office_manager.retrieve_contest_office(
                google_civic_election_id=candidate_to_office_link_add_election,
                office_held_we_vote_id=candidate_to_office_link_add_office_held_we_vote_id)
            if not results['success']:
                messages.add_message(request, messages.ERROR,
                                     'Cannot add Candidate-to-Office Link: office_we_vote_id missing.')
            elif results['contest_office_found']:
                contest_office = results['contest_office']
                contest_office_id = contest_office.id
                candidate_to_office_link_add_office_we_vote_id = contest_office.we_vote_id
                # Moved this to the candidate_to_office_link_list loop below
                # if positive_value_exists(candidate_to_office_link_add_election):
                #     results = election_manager.retrieve_election(
                #         google_civic_election_id=candidate_to_office_link_add_election)
                #     if results['election_found']:
                #         election = results['election']
                #         if positive_value_exists(election.election_day_text):
                #             candidate_ultimate_election_date = \
                #                 convert_we_vote_date_string_to_date_as_integer(election.election_day_text)
                #             year = election.election_day_text[:4]
                #             if year:
                #                 candidate_year = convert_to_int(year)
            else:
                # If not, create a new ContestOffice for this election
                from office.controllers import office_create_from_office_held
                create_results = office_create_from_office_held(
                    office_held_we_vote_id=candidate_to_office_link_add_office_held_we_vote_id,
                    google_civic_election_id=candidate_to_office_link_add_election)
                if create_results['success']:
                    if positive_value_exists(create_results['office_we_vote_id']):
                        candidate_to_office_link_add_office_we_vote_id = create_results['office_we_vote_id']
                    # Moved this to the candidate_to_office_link_list loop below
                    # if positive_value_exists(create_results['election_day_text']):
                    #     candidate_ultimate_election_date = \
                    #         convert_we_vote_date_string_to_date_as_integer(create_results['election_day_text'])
                    # if create_results['election_year']:
                    #     candidate_year = create_results['election_year']
        # ...and finally drop into the code below so a candidate_to_office_link is created
        if positive_value_exists(candidate_we_vote_id) and \
                positive_value_exists(candidate_to_office_link_add_office_we_vote_id) and \
                positive_value_exists(candidate_to_office_link_add_election):
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
            messages.add_message(
                request, messages.ERROR,
                "Cannot add Candidate-to-Office Link, missing one of these variables: "
                "candidate_we_vote_id: {candidate_we_vote_id}, "
                "candidate_to_office_link_add_election: {candidate_to_office_link_add_election}, "
                "candidate_to_office_link_add_office_we_vote_id: {candidate_to_office_link_add_office_we_vote_id}, "
                "".format(
                    candidate_to_office_link_add_election=candidate_to_office_link_add_election,
                    candidate_to_office_link_add_office_we_vote_id=candidate_to_office_link_add_office_we_vote_id,
                    candidate_we_vote_id=candidate_we_vote_id,
                ))
    elif positive_value_exists(candidate_to_office_link_add_election) or \
            positive_value_exists(candidate_to_office_link_add_office_we_vote_id) or \
            positive_value_exists(candidate_to_office_link_add_office_held_we_vote_id):
        messages.add_message(request, messages.ERROR, 'To add Candidate-to-Office Link, all three variables required.')

    # ##################################
    # Update "is_battleground_race" based on office data found through the link CandidateToOfficeLink
    # Also update "candidate_ultimate_election_date" and "candidate_year"
    results = candidate_list_manager.retrieve_candidate_to_office_link_list(
        candidate_we_vote_id_list=[candidate_we_vote_id],
        read_only=True)
    candidate_to_office_link_list = results['candidate_to_office_link_list']
    latest_election_date = 0
    latest_office_we_vote_id = ''
    for candidate_to_office_link in candidate_to_office_link_list:
        try:
            this_election = candidate_to_office_link.election()
            election_day_as_integer = convert_we_vote_date_string_to_date_as_integer(this_election.election_day_text)
            if election_day_as_integer > latest_election_date:
                candidate_ultimate_election_date = election_day_as_integer
                election_day_as_string = str(election_day_as_integer)
                year = election_day_as_string[:4]
                if year:
                    candidate_year = convert_to_int(year)
                latest_office_we_vote_id = candidate_to_office_link.contest_office_we_vote_id
        except Exception as e:
            status += "PROBLEM_GETTING_ELECTION_INFORMATION: " + str(e) + " "

    is_battleground_race = False
    if positive_value_exists(latest_office_we_vote_id):
        results = office_manager.retrieve_contest_office_from_we_vote_id(
            latest_office_we_vote_id,
            read_only=True,
        )
        if results['contest_office_found']:
            office = results['contest_office']
            is_battleground_race = positive_value_exists(office.is_battleground_race)

    contest_office_we_vote_id = ''
    state_code_from_office = ''
    if positive_value_exists(contest_office_id):
        results = office_manager.retrieve_contest_office_from_id(contest_office_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            contest_office_we_vote_id = contest_office.we_vote_id
            state_code_from_office = contest_office.state_code

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
        politician_manager = PoliticianManager()
        # If here, we specifically want to see if a politician exists, given the information submitted
        from wevote_functions.functions import add_to_list_if_positive_value_exists
        facebook_url_list = []
        facebook_url_list = add_to_list_if_positive_value_exists(facebook_url, facebook_url_list)
        full_name_list = []
        full_name_list = add_to_list_if_positive_value_exists(candidate_name, full_name_list)
        twitter_handle_list = []
        twitter_handle_list = add_to_list_if_positive_value_exists(candidate_twitter_handle, twitter_handle_list)
        twitter_handle_list = add_to_list_if_positive_value_exists(candidate_twitter_handle2, twitter_handle_list)
        twitter_handle_list = add_to_list_if_positive_value_exists(candidate_twitter_handle3, twitter_handle_list)
        match_results = politician_manager.retrieve_all_politicians_that_might_match_similar_object(
            facebook_url_list=facebook_url_list,
            full_name_list=full_name_list,
            twitter_handle_list=twitter_handle_list,
            maplight_id=maplight_id,
            return_close_matches=True,
            state_code=best_state_code,
            vote_smart_id=vote_smart_id,
            vote_usa_politician_id=vote_usa_politician_id)
        if match_results['politician_found']:
            messages.add_message(request, messages.INFO, 'Politician found.')
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
            status += "PROBLEM_RETRIEVING_CANDIDATE_DUPLICATES: " + str(e) + " "

    try:
        if existing_candidate_found:
            # We have found a duplicate for this election
            messages.add_message(request, messages.ERROR, 'This candidate is already saved for this election.')
            return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) + url_variables)
        elif candidate_on_stage_found:
            # Update

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
                if positive_value_exists(candidate_name) and positive_value_exists(best_state_code) \
                else False
            if required_candidate_variables:
                candidate_on_stage = CandidateCampaign(
                    candidate_name=candidate_name,
                    state_code=best_state_code,
                )
                candidate_on_stage_found = True
                messages.add_message(request, messages.INFO, 'New candidate created.')
            else:
                messages.add_message(request, messages.ERROR, 'Could not create new -- missing required variables.')
            #     if positive_value_exists(candidate_id):
            #         return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
            #                                     url_variables)
            #     else:
            #         return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) +
            #                                     url_variables)

        if positive_value_exists(candidate_on_stage_found):
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
            if candidate_contact_form_url is not False:
                candidate_on_stage.candidate_contact_form_url = candidate_contact_form_url
            if candidate_email is not False:
                candidate_on_stage.candidate_email = candidate_email
            if candidate_name is not False:
                candidate_on_stage.candidate_name = candidate_name
            if candidate_phone is not False:
                candidate_on_stage.candidate_phone = candidate_phone
            if candidate_twitter_handle is not False:
                candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
            if candidate_twitter_handle2 is not False:
                candidate_on_stage.candidate_twitter_handle2 = candidate_twitter_handle2
            if candidate_twitter_handle3 is not False:
                candidate_on_stage.candidate_twitter_handle3 = candidate_twitter_handle3
            if candidate_url is not False:
                candidate_on_stage.candidate_url = candidate_url
            if candidate_year is not False:
                if positive_value_exists(candidate_year):
                    candidate_on_stage.candidate_year = candidate_year
                # Turn this on if we want to be able to wipe out candidate_on_stage.candidate_year
                # else:
                #     candidate_on_stage.candidate_year = candidate_year
            if candidate_ultimate_election_date is not False:
                if positive_value_exists(candidate_ultimate_election_date):
                    candidate_on_stage.candidate_ultimate_election_date = candidate_ultimate_election_date
                # Turn this on if we want to be able to wipe out candidate_on_stage.candidate_ultimate_election_date
                # else:
                #     candidate_on_stage.candidate_ultimate_election_date = candidate_ultimate_election_date
            candidate_on_stage.do_not_display_on_ballot = do_not_display_on_ballot
            if facebook_url is not False:
                candidate_on_stage.facebook_url = facebook_url
            if google_civic_candidate_name is not False:
                candidate_on_stage.google_civic_candidate_name = google_civic_candidate_name
            if google_civic_candidate_name2 is not False:
                candidate_on_stage.google_civic_candidate_name2 = google_civic_candidate_name2
            if google_civic_candidate_name3 is not False:
                candidate_on_stage.google_civic_candidate_name3 = google_civic_candidate_name3
            if instagram_handle is not False:
                candidate_on_stage.instagram_handle = instagram_handle
            candidate_on_stage.is_battleground_race = is_battleground_race
            if linkedin_url is not False:
                candidate_on_stage.linkedin_url = linkedin_url
            if maplight_id is not False:
                candidate_on_stage.maplight_id = maplight_id
            if party is not False:
                candidate_on_stage.party = party
            if photo_url_from_vote_usa is not False:
                candidate_on_stage.photo_url_from_vote_usa = photo_url_from_vote_usa
            if politician_we_vote_id is not False:
                candidate_on_stage.politician_we_vote_id = politician_we_vote_id
            if state_code is not False:
                candidate_on_stage.state_code = state_code
            if twitter_url is not False:
                candidate_on_stage.twitter_url = twitter_url
            candidate_on_stage.twitter_handle_updates_failing = twitter_handle_updates_failing
            candidate_on_stage.twitter_handle2_updates_failing = twitter_handle2_updates_failing
            if vote_smart_id is not False:
                candidate_on_stage.vote_smart_id = vote_smart_id
            if vote_usa_politician_id is not False:
                candidate_on_stage.vote_usa_politician_id = vote_usa_politician_id
            if vote_usa_office_id is not False:
                candidate_on_stage.vote_usa_office_id = vote_usa_office_id
            if wikipedia_url is not False:
                candidate_on_stage.wikipedia_url = wikipedia_url
            if youtube_url is not False:
                candidate_on_stage.youtube_url = youtube_url
            if withdrawn_from_election:
                candidate_on_stage.withdrawn_from_election = withdrawn_from_election
                if positive_value_exists(withdrawal_date):
                    candidate_on_stage.withdrawal_date = withdrawal_date
                else:
                    candidate_on_stage.withdrawal_date = None

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
            candidate_id = candidate_on_stage.id
            candidate_we_vote_id = candidate_on_stage.we_vote_id
            ballotpedia_image_id = candidate_on_stage.ballotpedia_image_id
            ballotpedia_profile_image_url_https = candidate_on_stage.ballotpedia_profile_image_url_https

            messages.add_message(request, messages.INFO, 'CandidateCampaign updated.')

            # # Now add Candidate to Office Link
            # if positive_value_exists(candidate_we_vote_id) and positive_value_exists(contest_office_we_vote_id) and \
            #         positive_value_exists(google_civic_election_id):
            #     candidate_manager.get_or_create_candidate_to_office_link(
            #         candidate_we_vote_id=candidate_we_vote_id,
            #         contest_office_we_vote_id=contest_office_we_vote_id,
            #         google_civic_election_id=google_civic_election_id,
            #         state_code=best_state_code)

    except Exception as e:
        print('Could not save candidate (2).', e)
        messages.add_message(request, messages.ERROR, 'Could not save candidate (2), error: {error}'
                                                      ''.format(error=str(e)))
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    # if positive_value_exists(ballotpedia_image_id) and not positive_value_exists(ballotpedia_profile_image_url_https):
    #     results = retrieve_and_save_ballotpedia_candidate_images(candidate_on_stage)

    retrieve_candidate_from_database = False
    if positive_value_exists(refresh_from_twitter):
        status += "REFRESH_FROM_TWITTER "
        results = refresh_twitter_candidate_details(candidate_on_stage)
        if not results['success']:
            status += results['status']
        else:
            status += results['status']
        retrieve_candidate_from_database = True
    # elif profile_image_type_currently_active == 'UNKNOWN':
    #     # Prevent Twitter from updating
    #     pass
    elif positive_value_exists(candidate_twitter_handle) and not positive_value_exists(twitter_handle_updates_failing):
        status += "REFRESH_FROM_CANDIDATE_TWITTER_HANDLE "
        results = refresh_twitter_candidate_details(candidate_on_stage)
        if not results['success']:
            status += results['status']
        else:
            status += results['status']
        retrieve_candidate_from_database = True
    else:
        status += "DID_NOT_START_REFRESH_TWITTER "

    if retrieve_candidate_from_database:
        # Because we updated the candidate, through the refresh_twitter_candidate_details process,
        #  we want to retrieve the latest from database because we need to save the candidate below.
        candidate_on_stage = CandidateCampaign.objects.get(id=candidate_id)
        messages.add_message(request, messages.INFO, 'Twitter refreshed: ' + status)

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

    if candidate_on_stage_found and positive_value_exists(candidate_we_vote_id):
        from politician.controllers import update_parallel_fields_with_years_in_related_objects
        results = update_parallel_fields_with_years_in_related_objects(
            field_key_root='is_battleground_race_',
            master_we_vote_id_updated=candidate_we_vote_id,
        )
        if not results['success']:
            status += results['status']
            status += "FAILED_TO_UPDATE_PARALLEL_FIELDS_FROM_CANDIDATE "
            messages.add_message(request, messages.ERROR, status)

    # ##################################
    # If linked to a Politician, bring over some data from Politician
    if candidate_on_stage_found and positive_value_exists(candidate_on_stage.politician_we_vote_id):
        try:
            politician_manager = PoliticianManager()
            results = politician_manager.retrieve_politician(
                politician_we_vote_id=candidate_on_stage.politician_we_vote_id,
                read_only=True)
            if results['politician_found']:
                politician = results['politician']
                if positive_value_exists(politician.id) and candidate_on_stage.politician_id != politician.id:
                    # make sure that both politician_id exists
                    candidate_on_stage.politician_id = politician.id
                candidate_on_stage.linked_campaignx_we_vote_id = politician.linked_campaignx_we_vote_id
                candidate_on_stage.linked_campaignx_we_vote_id_date_last_updated = \
                    politician.linked_campaignx_we_vote_id_date_last_updated
                candidate_on_stage.seo_friendly_path = politician.seo_friendly_path
                candidate_on_stage.seo_friendly_path_date_last_updated = politician.seo_friendly_path_date_last_updated
                candidate_on_stage.save()
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 'Could not save candidate with refreshed politician data:' + str(e))

    url_variables = "?null=1"
    if positive_value_exists(show_all_twitter_search_results):
        url_variables += "&show_all_twitter_search_results=1#twitter_link_possibility_list"

    if redirect_to_candidate_list:
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_candidates=' + str(candidate_year) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&show_candidates_with_twitter_options=1' +
                                    '&page=' + str(page))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    '&candidate_year=' + str(candidate_year) +
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

    # Loop through all the candidates in this election
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
def candidate_politician_match_this_year_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_year = request.GET.get('candidate_year', 0)
    state_code = request.GET.get('state_code', '')

    # We only want to process if a year comes in
    if not positive_value_exists(candidate_year):
        messages.add_message(request, messages.ERROR, "Year required.")
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()))

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_all_candidates_for_one_year(
        candidate_year=candidate_year,
        candidates_limit=1000,
        is_missing_politician_we_vote_id=True,
        limit_to_this_state_code=state_code,
        return_list_of_objects=True,
    )
    candidate_list = results['candidate_list_objects']

    if len(candidate_list) == 0:
        messages.add_message(request, messages.INFO, "No candidates found for year: {candidate_year}.".format(
            candidate_year=candidate_year))
        return HttpResponseRedirect(
            reverse('candidate:candidate_list', args=()) + "?show_this_year_of_candidates={candidate_year}"
                                                           "".format(
                                                           candidate_year=candidate_year))

    num_candidates_reviewed = 0
    num_that_already_have_politician_we_vote_id = 0
    new_politician_created = 0
    existing_politician_found = 0
    multiple_politicians_found = 0
    other_results = 0

    message = "About to loop through all of the candidates this year to make sure we have a politician record."
    print_to_log(logger, exception_message_optional=message)

    # Loop through all the candidates from this year
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

    message = "Year: {candidate_year}, " \
              "{num_candidates_reviewed} candidates reviewed, " \
              "{num_that_already_have_politician_we_vote_id} Candidates that already have Politician Ids, " \
              "{new_politician_created} politicians just created, " \
              "{existing_politician_found} politicians found that already exist, " \
              "{multiple_politicians_found} times we found multiple politicians and could not link, " \
              "{other_results} other results". \
              format(candidate_year=candidate_year,
                     num_candidates_reviewed=num_candidates_reviewed,
                     num_that_already_have_politician_we_vote_id=num_that_already_have_politician_we_vote_id,
                     new_politician_created=new_politician_created,
                     existing_politician_found=existing_politician_found,
                     multiple_politicians_found=multiple_politicians_found,
                     other_results=other_results)

    print_to_log(logger, exception_message_optional=message)
    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                "?show_this_year_of_candidates={candidate_year}"
                                "&state_code={state_code}"
                                "".format(
                                candidate_year=candidate_year,
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

    is_post = True if request.method == 'POST' else False

    if is_post:
        merge = request.POST.get('merge', False)
        skip = request.POST.get('skip', False)

        # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
        candidate_year = request.POST.get('candidate_year', 0)
        candidate1_we_vote_id = request.POST.get('candidate1_we_vote_id', 0)
        candidate2_we_vote_id = request.POST.get('candidate2_we_vote_id', 0)
        google_civic_election_id = request.POST.get('google_civic_election_id', 0)
        redirect_to_candidate_list = request.POST.get('redirect_to_candidate_list', False)
        remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
        state_code = request.POST.get('state_code', '')
    else:
        merge = request.GET.get('merge', False)
        skip = request.GET.get('skip', False)

        # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
        candidate_year = request.GET.get('candidate_year', 0)
        candidate1_we_vote_id = request.GET.get('candidate1_we_vote_id', 0)
        candidate2_we_vote_id = request.GET.get('candidate2_we_vote_id', 0)
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
        redirect_to_candidate_list = request.GET.get('redirect_to_candidate_list', False)
        remove_duplicate_process = request.GET.get('remove_duplicate_process', False)
        state_code = request.GET.get('state_code', '')

    if positive_value_exists(skip):
        results = candidate_manager.update_or_create_candidates_are_not_duplicates(
            candidate1_we_vote_id, candidate2_we_vote_id)
        if not results['new_candidates_are_not_duplicates_created']:
            messages.add_message(request, messages.ERROR, 'Could not save candidates_are_not_duplicates entry: ' +
                                 results['status'])
        messages.add_message(request, messages.INFO, 'Prior candidates skipped, and not merged.')
        return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                                    "?candidate_year=" + str(candidate_year) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    candidate1_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate1_we_vote_id, read_only=True)
    if candidate1_results['candidate_found']:
        candidate1_on_stage = candidate1_results['candidate']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve candidate 1.')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_candidates=' + str(candidate_year) +
                                    '&state_code=' + str(state_code))

    candidate2_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate2_we_vote_id, read_only=True)
    if candidate2_results['candidate_found']:
        candidate2_on_stage = candidate2_results['candidate']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve candidate 2.')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_candidates=' + str(candidate_year) +
                                    '&state_code=' + str(state_code))

    # Gather choices made from merge form
    conflict_values = figure_out_candidate_conflict_values(candidate1_on_stage, candidate2_on_stage)
    admin_merge_choices = {}
    for attribute in CANDIDATE_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            if is_post:
                choice = request.POST.get(attribute + '_choice', '')
            else:
                choice = request.GET.get(attribute + '_choice', '')
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
                                    '&candidate_year=' + str(candidate_year) +
                                    "&auto_merge_off=1" +
                                    "&state_code=" + str(state_code))

    if redirect_to_candidate_list:
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_candidates=' + str(candidate_year) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('candidate:find_and_merge_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    '&candidate_year=' + str(candidate_year) +
                                    "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate1_on_stage.id,)))


@login_required
def find_and_merge_duplicate_candidates_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    ignore_candidate_id_list = []
    candidate_year = request.GET.get('candidate_year', 0)
    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', "")
    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()
    election_manager = ElectionManager()

    retrieve_by_candidate_year = False
    retrieve_by_election_id_list = False
    google_civic_election_id_list = []
    if positive_value_exists(candidate_year):
        retrieve_by_candidate_year = True
    elif positive_value_exists(google_civic_election_id):
        google_civic_election_id_list = [google_civic_election_id]
        retrieve_by_election_id_list = True
    else:
        results = election_manager.retrieve_upcoming_google_civic_election_id_list()
        google_civic_election_id_list = results['upcoming_google_civic_election_id_list']
        retrieve_by_election_id_list = True

    candidate_list = []
    if retrieve_by_candidate_year:
        results = candidate_list_manager.retrieve_all_candidates_for_one_year(
            candidate_year=candidate_year,
            limit_to_this_state_code=state_code,
            return_list_of_objects=True,
        )
        candidate_list = results['candidate_list_objects']
    elif retrieve_by_election_id_list:
        results = candidate_list_manager.retrieve_candidates_for_specific_elections(
            google_civic_election_id_list=google_civic_election_id_list,
            return_list_of_objects=True)
        candidate_list = results['candidate_list_objects']

    # Loop through all the candidates in this election to see how many have possible duplicates
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

    # Loop through all the candidates in this year or election
    ignore_candidate_id_list = []
    for we_vote_candidate in candidate_list:
        # Add current candidate entry to ignore list
        ignore_candidate_id_list.append(we_vote_candidate.we_vote_id)
        # Now check to for other candidates we have labeled as "not a duplicate"
        not_a_duplicate_list = candidate_manager.fetch_candidates_are_not_duplicates_list_we_vote_ids(
            we_vote_candidate.we_vote_id)

        ignore_candidate_id_list += not_a_duplicate_list

        results = find_duplicate_candidate(we_vote_candidate, ignore_candidate_id_list, read_only=True)
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

            if merge_results['candidates_merged']:
                candidate = merge_results['candidate']
                messages.add_message(request, messages.INFO, "Candidate {candidate_name} automatically merged."
                                                             "".format(candidate_name=candidate.candidate_name))
            else:
                # This view function takes us to displaying a template
                messages.add_message(request, messages.INFO, merge_results['status'])
                remove_duplicate_process = True  # Try to find another candidate to merge after finishing
                return render_candidate_merge_form(
                    request,
                    candidate_option1_for_template,
                    candidate_option2_for_template,
                    results['candidate_merge_conflict_values'],
                    candidate_year=candidate_year,
                    remove_duplicate_process=remove_duplicate_process)

    if retrieve_by_candidate_year:
        message = "No more duplicate candidates found for the year {candidate_year}" \
                  "".format(candidate_year=candidate_year)
        if positive_value_exists(state_code):
            message += " in {state_code}".format(state_code=state_code)
        message += "."
    elif retrieve_by_election_id_list:
        message = "No more duplicate candidates found for election {election_id}" \
                  "".format(election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            message += " in {state_code}".format(state_code=state_code)
        message += "."
    else:
        message = "No more duplicate candidates found"
        if positive_value_exists(state_code):
            message += " in {state_code}".format(state_code=state_code)
        message += "."

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                "?google_civic_election_id={google_civic_election_id}"
                                "&show_this_year_of_candidates={show_this_year_of_candidates}"
                                "&state_code={state_code}"
                                "".format(
                                    google_civic_election_id=google_civic_election_id,
                                    show_this_year_of_candidates=candidate_year,
                                    state_code=state_code))


def render_candidate_merge_form(
        request,
        candidate_option1_for_template,
        candidate_option2_for_template,
        candidate_merge_conflict_values,
        candidate_year=0,
        remove_duplicate_process=True):

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
        'candidate_year':                                   candidate_year,
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

    candidate_year = request.GET.get('candidate_year', 0)
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

    results = find_duplicate_candidate(candidate, ignore_candidate_id_list, read_only=True)

    # If we find candidates to merge, stop and ask for confirmation
    if results['candidate_merge_possibility_found']:
        candidate_option1_for_template = candidate
        candidate_option2_for_template = results['candidate_merge_possibility']

        # This view function takes us to displaying a template
        remove_duplicate_process = True  # Try to find another candidate to merge after finishing
        return render_candidate_merge_form(
            request,
            candidate_option1_for_template,
            candidate_option2_for_template,
            results['candidate_merge_conflict_values'],
            candidate_year=candidate_year,
            remove_duplicate_process=remove_duplicate_process)

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
def remove_duplicate_candidates_view(request):
    """
    For one state, remove candidate entries that are mostly empty, and created accidentally in bulk.
    Includes default analysis mode, so we can double-check before deleting, and then delete mode.
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_name = request.GET.get('candidate_name', '')
    confirm_delete = positive_value_exists(request.GET.get('confirm_delete', False))
    delete_submitted = positive_value_exists(request.GET.get('delete_submitted', False))
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
    state_code = request.GET.get('state_code', '')
    related_candidate_list = []
    status = ''
    success = True

    missing_variables = False
    if not positive_value_exists(candidate_name):
        messages.add_message(request, messages.ERROR, "Candidate name required.")
        missing_variables = True
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Election ID required.")
        missing_variables = True
    if not positive_value_exists(state_code):
        messages.add_message(request, messages.ERROR, "State Code required.")
        missing_variables = True

    if missing_variables:
        return HttpResponseRedirect(
            reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}&state_code={state}"
                                                           "".format(
                                                           state=state_code,
                                                           var=google_civic_election_id))

    from candidate.models import CandidateCampaign
    try:
        queryset = CandidateCampaign.objects.all()
        queryset = queryset.filter(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id=''))
        queryset = queryset.filter(candidate_name__iexact=candidate_name)
        queryset = queryset.filter(google_civic_election_id=google_civic_election_id)
        queryset = queryset.filter(state_code__iexact=state_code)
        related_candidate_list = list(queryset)

        if delete_submitted:
            delete_queryset = queryset
            do_not_delete_list = []
            for candidate in related_candidate_list:
                if positive_value_exists(candidate.id):
                    variable_name = "do_not_delete_candidate_" + str(candidate.id)
                    if positive_value_exists(request.GET.get(variable_name, False)):
                        do_not_delete_list.append(candidate.id)
            delete_queryset = delete_queryset.exclude(id__in=do_not_delete_list)
            if confirm_delete:
                delete_count = delete_queryset.count()
                delete_queryset.delete()
                messages.add_message(request, messages.INFO,
                                     "{delete_count} candidate entries deleted."
                                     "".format(delete_count=delete_count))
            else:
                messages.add_message(request, messages.ERROR,
                                     "You must confirm that you want to delete these candidates.")
                delete_count = delete_queryset.count()
                messages.add_message(request, messages.INFO,
                                     "{delete_count} candidate entries to be deleted."
                                     "".format(delete_count=delete_count))
    except Exception as e:
        status += "CANDIDATE_CAMPAIGN_RETRIEVE_FAILED: " + str(e) + " "

    modified_related_candidate_list = []
    for candidate in related_candidate_list:
        if positive_value_exists(candidate.id):
            variable_name = "do_not_delete_candidate_" + str(candidate.id)
            candidate.do_not_delete = positive_value_exists(request.GET.get(variable_name, False))
            modified_related_candidate_list.append(candidate)

    template_values = {
        'candidate_name':           candidate_name,
        'google_civic_election_id': google_civic_election_id,
        'politician_we_vote_id':    politician_we_vote_id,
        'related_candidate_list':   modified_related_candidate_list,
        'state_code':               state_code,
    }
    return render(request, 'candidate/remove_duplicate_candidates_preview.html', template_values)


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
        # Don't include the candidate whose page this is
        candidate_query = candidate_query.exclude(we_vote_id__iexact=candidate_we_vote_id)

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
        results = find_duplicate_candidate(candidate_on_stage, ignore_candidate_we_vote_id_list, read_only=True)
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
def candidate_create_process_view(request):
    """
    Delete this candidate
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    politician_we_vote_id = request.GET.get('politician_we_vote_id', '')

    from candidate.controllers import candidate_create_from_politician
    results = candidate_create_from_politician(politician_we_vote_id=politician_we_vote_id)
    candidate_id = 0
    if results['candidate_found']:
        candidate = results['candidate']
        candidate_id = candidate.id
    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


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

    candidate_year = request.GET.get('candidate_year', 0)
    candidate1_we_vote_id = request.GET.get('candidate1_we_vote_id', 0)
    candidate2_we_vote_id = request.GET.get('candidate2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_manager = CandidateManager()
    candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate1_we_vote_id, read_only=True)
    if not candidate_results['candidate_found']:
        messages.add_message(request, messages.ERROR, "Candidate1 not found.")
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    candidate_option1_for_template = candidate_results['candidate']

    candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate2_we_vote_id, read_only=True)
    if not candidate_results['candidate_found']:
        messages.add_message(request, messages.ERROR, "Candidate2 not found.")
        return HttpResponseRedirect(reverse('candidate:candidate_summary', args=(candidate_option1_for_template.id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    candidate_option2_for_template = candidate_results['candidate']

    candidate_merge_conflict_values = figure_out_candidate_conflict_values(
        candidate_option1_for_template, candidate_option2_for_template)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_candidate_merge_form(
        request,
        candidate_option1_for_template,
        candidate_option2_for_template,
        candidate_merge_conflict_values,
        candidate_year=candidate_year,
        remove_duplicate_process=remove_duplicate_process)
