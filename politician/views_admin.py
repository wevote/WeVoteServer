# politician/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import re
from base64 import b64encode
import json
import string
from datetime import datetime, timedelta
import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Q
from django.db.models.functions import Length
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.timezone import localtime, now
from django.urls import reverse
import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from campaign.models import CampaignXManager
from candidate.controllers import retrieve_candidate_photos
from candidate.models import CandidateCampaign, CandidateListManager, CandidateManager, CandidateToOfficeLink, \
    KIND_OF_LOG_ENTRY_ANALYSIS_COMMENT, KIND_OF_LOG_ENTRY_LINK_ADDED, PROFILE_IMAGE_TYPE_BALLOTPEDIA, \
    PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_UPLOADED, PROFILE_IMAGE_TYPE_VOTE_USA, PROFILE_IMAGE_TYPE_WIKIPEDIA
from config.base import get_environment_variable
from election.models import Election
from exception.models import handle_record_found_more_than_one_exception, \
    handle_record_not_found_exception, handle_record_not_saved_exception, print_to_log
from image.controllers import create_resized_images, organize_object_photo_fields_based_on_image_type_currently_active
from import_export_ballotpedia.controllers import get_photo_url_from_ballotpedia
from import_export_vote_smart.models import VoteSmartRatingOneCandidate
from import_export_vote_smart.votesmart_local import VotesmartApiError
from import_export_wikipedia.controllers import get_photo_url_from_wikipedia
from office.models import ContestOffice
from position.models import PositionEntered, PositionListManager
from representative.models import Representative, RepresentativeManager
from volunteer_task.controllers import change_tracking, change_tracking_boolean
# from politician.controllers_recommendation import update_recommend  # 2024-05-15: Causing problems on live servers
from volunteer_task.models import VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS, \
    VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION, VolunteerTaskManager
from voter.models import fetch_voter_from_voter_device_link, voter_has_authority, VoterManager
from wevote_functions.functions import convert_to_int, convert_to_political_party_constant, \
    extract_first_name_from_full_name, extract_instagram_handle_from_text_string, \
    extract_middle_name_from_full_name, extract_last_name_from_full_name, \
    extract_state_from_ocd_division_id, extract_twitter_handle_from_text_string, get_voter_api_device_id, \
    positive_value_exists, STATE_CODE_MAP, display_full_name_with_correct_capitalization
from wevote_functions.functions_date import convert_date_to_we_vote_date_string, \
    convert_we_vote_date_string_to_date_as_integer, generate_localized_datetime_from_obj
from wevote_settings.constants import IS_BATTLEGROUND_YEARS_AVAILABLE
from .controllers import add_alternate_names_to_next_spot, add_twitter_handle_to_next_politician_spot, \
    fetch_duplicate_politician_count, figure_out_politician_conflict_values, find_duplicate_politician, \
    generate_campaignx_for_politician, politician_save_photo_from_file_reader, \
    update_politician_details_from_candidate, \
    merge_if_duplicate_politicians, merge_these_two_politicians, politicians_import_from_master_server
from .models import Politician, PoliticianChangeLog, PoliticianManager, POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED, \
    POLITICIAN_UNIQUE_IDENTIFIERS, PoliticiansArePossibleDuplicates, POLITICAL_DATA_MANAGER, UNKNOWN, \
    RecommendedPoliticianLinkByPolitician
from politician.controllers_generate_color import generate_background, validate_hex
POLITICIANS_SYNC_URL = get_environment_variable("POLITICIANS_SYNC_URL")  # politiciansSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def compare_two_politicians_for_merge_view(request):
    status = ''
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician1_we_vote_id = request.GET.get('politician1_we_vote_id', 0)
    politician2_we_vote_id = request.GET.get('politician2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', '')

    politician_manager = PoliticianManager()
    politician_results = politician_manager.retrieve_politician(
        politician_we_vote_id=politician1_we_vote_id,
        read_only=True)
    if not politician_results['politician_found']:
        messages.add_message(request, messages.ERROR, "Politician1 not found.")
        return HttpResponseRedirect(
            reverse('politician:politician_list', args=()) +
            "?google_civic_election_id=" + str(google_civic_election_id) +
            "&state_code=" + str(state_code))

    politician_option1_for_template = politician_results['politician']

    politician_results = politician_manager.retrieve_politician(
        politician_we_vote_id=politician2_we_vote_id,
        read_only=True)
    if not politician_results['politician_found']:
        messages.add_message(request, messages.ERROR, "Politician2 not found.")
        return HttpResponseRedirect(
            reverse('politician:politician_edit', args=(politician_option1_for_template.id,)) +
            "?google_civic_election_id=" + str(google_civic_election_id) +
            "&state_code=" + str(state_code))

    politician_option2_for_template = politician_results['politician']

    if politician1_we_vote_id == politician2_we_vote_id:
        messages.add_message(request, messages.ERROR, "These politicians are already merged.")
        return HttpResponseRedirect(
            reverse('politician:politician_edit', args=(politician_option1_for_template.id,)) +
            "?google_civic_election_id=" + str(google_civic_election_id) +
            "&state_code=" + str(state_code))

    conflict_results = figure_out_politician_conflict_values(
        politician_option1_for_template, politician_option2_for_template)
    politician_merge_conflict_values = conflict_results['politician_merge_conflict_values']
    if not conflict_results['success']:
        status += conflict_results['status']
        messages.add_message(request, messages.ERROR, status)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_politician_merge_form(
        request,
        politician_option1_for_template,
        politician_option2_for_template,
        politician_merge_conflict_values,
        remove_duplicate_process)


@login_required
def find_and_merge_duplicate_politicians_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    state_code = request.GET.get('state_code', "")
    status = ""
    politician_manager = PoliticianManager()

    queryset = PoliticiansArePossibleDuplicates.objects.using('readonly').all()
    if positive_value_exists(state_code):
        queryset = queryset.filter(state_code__iexact=state_code)
    queryset = queryset.exclude(politician1_we_vote_id=None)
    queryset = queryset.exclude(politician2_we_vote_id=None)
    queryset_politician1 = queryset.values_list('politician1_we_vote_id', flat=True).distinct()
    exclude_politician1_we_vote_id_list = list(queryset_politician1)
    queryset_politician2 = queryset.values_list('politician2_we_vote_id', flat=True).distinct()
    exclude_politician2_we_vote_id_list = list(queryset_politician2)
    exclude_politician_we_vote_id_list = \
        list(set(exclude_politician1_we_vote_id_list + exclude_politician2_we_vote_id_list))

    politician_query = Politician.objects.using('readonly').all()
    politician_query = politician_query.exclude(we_vote_id__in=exclude_politician_we_vote_id_list)
    if positive_value_exists(state_code):
        politician_query = politician_query.filter(state_code__iexact=state_code)
    politician_list = list(politician_query)

    # # Loop through to see how many have possible duplicates
    # if positive_value_exists(find_number_of_duplicates):
    #     duplicate_count = 0
    #     ignore_politician_id_list = []
    #     for we_vote_politician in politician_list:
    #         # Note that we don't reset the ignore_politician_list, so we don't search for a duplicate both directions
    #         ignore_politician_id_list.append(we_vote_politician.we_vote_id)
    #         duplicate_count_temp = fetch_duplicate_politician_count(
    #             we_vote_politician, ignore_politician_id_list)
    #         duplicate_count += duplicate_count_temp
    #
    #     if positive_value_exists(duplicate_count):
    #         messages.add_message(request, messages.INFO,
    #                              "There are approximately {duplicate_count} "
    #                              "possible duplicates."
    #                              "".format(duplicate_count=duplicate_count))

    try:
        # Give the volunteer who entered this credit
        volunteer_task_manager = VolunteerTaskManager()
        task_results = volunteer_task_manager.create_volunteer_task_completed(
            action_constant=VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS,
            request=request,
        )
    except Exception as e:
        status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    # Loop through all the politicians in this election
    for we_vote_politician in politician_list:
        if we_vote_politician.we_vote_id in exclude_politician_we_vote_id_list:
            continue
        # Start ignore list with entries already reviewed
        ignore_politician_id_list = exclude_politician_we_vote_id_list
        # Add current entry to ignore list
        ignore_politician_id_list.append(we_vote_politician.we_vote_id)
        # Now check for others we have already labeled as "not a duplicate"
        not_a_duplicate_list = politician_manager.fetch_politicians_are_not_duplicates_list_we_vote_ids(
            we_vote_politician.we_vote_id)
        ignore_politician_id_list += not_a_duplicate_list

        results = find_duplicate_politician(we_vote_politician, ignore_politician_id_list, read_only=True)

        # If we find politicians to merge, store them for review
        if results['politician_merge_possibility_found']:
            politician_option1_for_template = we_vote_politician
            politician_option2_for_template = results['politician_merge_possibility']

            # Can we automatically merge these politicians?
            merge_results = merge_if_duplicate_politicians(
                politician_option1_for_template,
                politician_option2_for_template,
                results['politician_merge_conflict_values'])

            if merge_results['politicians_merged']:
                politician = merge_results['politician']
                if politician.we_vote_id not in exclude_politician_we_vote_id_list:
                    exclude_politician_we_vote_id_list.append(politician.we_vote_id)
                if we_vote_politician.we_vote_id not in exclude_politician_we_vote_id_list:
                    exclude_politician_we_vote_id_list.append(we_vote_politician.we_vote_id)
                PoliticiansArePossibleDuplicates.objects.create(
                    politician1_we_vote_id=politician.we_vote_id,
                    politician2_we_vote_id=None,
                    state_code=state_code,
                )
                PoliticiansArePossibleDuplicates.objects.create(
                    politician1_we_vote_id=we_vote_politician.we_vote_id,
                    politician2_we_vote_id=None,
                    state_code=state_code,
                )
                messages.add_message(request, messages.INFO,
                                     "Politician {politician_name} automatically merged."
                                     "".format(politician_name=politician.politician_name))
            else:
                # Add an entry showing that this is a possible match
                PoliticiansArePossibleDuplicates.objects.create(
                    politician1_we_vote_id=we_vote_politician.we_vote_id,
                    politician2_we_vote_id=politician_option2_for_template.we_vote_id,
                    state_code=state_code,
                )
                if politician_option2_for_template.we_vote_id not in exclude_politician_we_vote_id_list:
                    exclude_politician_we_vote_id_list.append(politician_option2_for_template.we_vote_id)
        else:
            # No matches found
            PoliticiansArePossibleDuplicates.objects.create(
                politician1_we_vote_id=we_vote_politician.we_vote_id,
                politician2_we_vote_id=None,
                state_code=state_code,
            )

    return HttpResponseRedirect(reverse('politician:duplicates_list', args=()) +
                                "?state_code={state_code}"
                                "".format(state_code=state_code))


def render_politician_merge_form(
        request,
        politician_option1_for_template,
        politician_option2_for_template,
        politician_merge_conflict_values,
        remove_duplicate_process=True):
    candidate_list_manager = CandidateListManager()

    state_code = ''
    if hasattr(politician_option1_for_template, 'state_code'):
        state_code = politician_option1_for_template.state_code
    if hasattr(politician_option2_for_template, 'state_code'):
        state_code = politician_option2_for_template.state_code

    # Get info about candidates linked to each politician
    politician1_linked_candidates_count = 0
    politician1_linked_candidate_district_names = ''
    politician1_linked_candidate_names = ''
    politician1_linked_candidate_offices = ''
    politician1_linked_candidate_photos = []
    politician1_candidate_results = candidate_list_manager.retrieve_candidates_from_politician(
        politician_id=politician_option1_for_template.id,
        politician_we_vote_id=politician_option1_for_template.we_vote_id,
        read_only=True)
    if politician1_candidate_results['candidate_list_found']:
        is_first = True
        is_first_office = True
        for one_candidate in politician1_candidate_results['candidate_list']:
            politician1_linked_candidates_count += 1
            if is_first:
                is_first = False
            else:
                politician1_linked_candidate_names += ', '
            politician1_linked_candidate_names += one_candidate.candidate_name
            if positive_value_exists(one_candidate.candidate_year):
                politician1_linked_candidate_names += ' (' + str(one_candidate.candidate_year) + ')'
            if positive_value_exists(one_candidate.we_vote_hosted_profile_image_url_large):
                politician1_linked_candidate_photos.append(one_candidate.we_vote_hosted_profile_image_url_large)
            results = candidate_list_manager.retrieve_all_offices_for_candidate(
                candidate_we_vote_id=one_candidate.we_vote_id,
                read_only=True)
            if results['office_list_found']:
                for one_office in results['office_list']:
                    if is_first_office:
                        is_first_office = False
                    else:
                        politician1_linked_candidate_offices += ', '
                        politician1_linked_candidate_district_names += ', '
                    politician1_linked_candidate_offices += one_office.office_name
                    politician1_linked_candidate_district_names += str(one_office.district_name)
    politician_option1_for_template.linked_candidates_count = politician1_linked_candidates_count
    politician_option1_for_template.linked_candidate_district_names = politician1_linked_candidate_district_names
    politician_option1_for_template.linked_candidate_names = politician1_linked_candidate_names
    politician_option1_for_template.linked_candidate_offices = politician1_linked_candidate_offices
    politician_option1_for_template.linked_candidate_photos = politician1_linked_candidate_photos

    politician2_linked_candidates_count = 0
    politician2_linked_candidate_district_names = ''
    politician2_linked_candidate_names = ''
    politician2_linked_candidate_offices = ''
    politician2_linked_candidate_photos = []
    politician2_candidate_results = candidate_list_manager.retrieve_candidates_from_politician(
        politician_id=politician_option2_for_template.id,
        politician_we_vote_id=politician_option2_for_template.we_vote_id,
        read_only=True)
    if politician2_candidate_results['candidate_list_found']:
        is_first = True
        is_first_office = True
        for one_candidate in politician2_candidate_results['candidate_list']:
            politician2_linked_candidates_count += 1
            if is_first:
                is_first = False
            else:
                politician2_linked_candidate_names += ', '
            politician2_linked_candidate_names += one_candidate.candidate_name
            if positive_value_exists(one_candidate.candidate_year):
                politician2_linked_candidate_names += ' (' + str(one_candidate.candidate_year) + ')'
            if positive_value_exists(one_candidate.we_vote_hosted_profile_image_url_large):
                politician2_linked_candidate_photos.append(one_candidate.we_vote_hosted_profile_image_url_large)
            results = candidate_list_manager.retrieve_all_offices_for_candidate(
                candidate_we_vote_id=one_candidate.we_vote_id,
                read_only=True)
            if results['office_list_found']:
                for one_office in results['office_list']:
                    if is_first_office:
                        is_first_office = False
                    else:
                        politician2_linked_candidate_offices += ', '
                        politician2_linked_candidate_district_names += ', '
                    politician2_linked_candidate_offices += one_office.office_name
                    politician2_linked_candidate_district_names += str(one_office.district_name)
    politician_option2_for_template.linked_candidates_count = politician2_linked_candidates_count
    politician_option2_for_template.linked_candidate_district_names = politician2_linked_candidate_district_names
    politician_option2_for_template.linked_candidate_names = politician2_linked_candidate_names
    politician_option2_for_template.linked_candidate_offices = politician2_linked_candidate_offices
    politician_option2_for_template.linked_candidate_photos = politician2_linked_candidate_photos

    messages_on_stage = get_messages(request)
    template_values = {
        'conflict_values':          politician_merge_conflict_values,
        'messages_on_stage':        messages_on_stage,
        'politician_option1':       politician_option1_for_template,
        'politician_option2':       politician_option2_for_template,
        'remove_duplicate_process': remove_duplicate_process,
        'state_code':               state_code,
    }
    return render(request, 'politician/politician_merge.html', template_values)


@login_required
def politicians_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in POLITICIANS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = politicians_import_from_master_server(request, state_code)

    if not results['success']:
        if 'POLITICIAN_LIST_MISSING' in results['status']:
            messages.add_message(request, messages.INFO,
                                 'Politician import completed, and it returned no politicians, but this is not '
                                 'necessarily a problem!  It might be that are no local politicians running for office '
                                 'in this election.')
        else:
            messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Politician import completed. '
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
def politician_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    politician_search = request.GET.get('politician_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    # run_scripts = positive_value_exists(request.GET.get('run_scripts', False))
    run_scripts = True
    show_all = positive_value_exists(request.GET.get('show_all', False))
    show_battleground = positive_value_exists(request.GET.get('show_battleground', False))
    show_related_candidates = positive_value_exists(request.GET.get('show_related_candidates', False))
    show_ocd_id_state_mismatch = positive_value_exists(request.GET.get('show_ocd_id_state_mismatch', False))
    show_politicians_with_email = positive_value_exists(request.GET.get('show_politicians_with_email', False))

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    # When we were preparing to remove the field 'politician_email_address', we wanted to make sure
    # they had all be transferred. This verifies it.
    # # Are there any entries where politician_email doesn't match politician_email_address?
    # politician_query = Politician.objects.all()
    # politician_query = politician_query.exclude(
    #     Q(politician_email_address__isnull=True) |
    #     Q(politician_email_address="")
    # )
    # # Do not return entries where the values already match
    # politician_query = politician_query.exclude(politician_email__iexact=F('politician_email_address'))
    # list_found = list(politician_query[:10])  # Only find the first 10 entries
    # if len(list_found) > 0:
    #     we_vote_id_string = ''
    #     for one_politician in list_found:
    #         we_vote_id_string += str(one_politician.we_vote_id) + " "
    #     messages.add_message(request, messages.ERROR,
    #                          'politician_email mismatch with politician_email_address: ' + str(we_vote_id_string))

    # Make sure we have a version of the politician's name without a middle initial (for matching endorsements)
    generate_google_civic_name_alternates = True
    number_to_generate = 1000
    if generate_google_civic_name_alternates and positive_value_exists(state_code) and run_scripts:
        politician_query = Politician.objects.all()
        politician_query = politician_query.filter(google_civic_name_alternates_generated=False)
        politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_generate if total_to_convert > number_to_generate else 0
        politician_list_to_convert = list(politician_query[:number_to_generate])
        update_list = []
        updates_needed = False
        updates_made = 0
        for one_politician in politician_list_to_convert:
            results = add_alternate_names_to_next_spot(
                politician=one_politician,
            )
            if results['values_changed']:
                politician = results['politician']
                politician.google_civic_name_alternates_generated = True
                update_list.append(politician)
                updates_needed = True
                updates_made += 1
            elif results['success']:
                one_politician.google_civic_name_alternates_generated = True
                update_list.append(one_politician)
                updates_needed = True
        if updates_needed:
            try:
                Politician.objects.bulk_update(update_list, [
                    'google_civic_name_alternates_generated',
                    'google_civic_candidate_name',
                    'google_civic_candidate_name2',
                    'google_civic_candidate_name3',
                ])
                messages.add_message(request, messages.INFO,
                                     "{updates_made:,} google_civic_name_alternates_generated. "
                                     "{total_to_convert_after:,} remaining."
                                     "".format(total_to_convert_after=total_to_convert_after,
                                               updates_made=updates_made))
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     "ERROR with google_civic_name_alternates_generated: {e} "
                                     "".format(e=e))

    generate_backgrounds = True
    number_to_generate = 10
    if generate_backgrounds and positive_value_exists(state_code) and run_scripts:
        politician_query = Politician.objects.all()
        politician_query = politician_query.filter(state_code__iexact=state_code)
        politician_query = politician_query.exclude(profile_image_background_color_needed=False)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_generate if total_to_convert > number_to_generate else 0
        politician_list_to_convert = list(politician_query[:number_to_generate])
        update_list = []
        politicians_updated = 0
        politicians_not_updated = 0

        for politician in politician_list_to_convert:
            politician.profile_image_background_color_needed = False
            if positive_value_exists(politician.we_vote_hosted_profile_image_url_large):
                hex = generate_background(politician)
                politician.profile_image_background_color = hex
                politicians_updated += 1
                update_list.append(politician)
            else:
                politicians_not_updated += 1

        if len(update_list) > 0:
            try:
                Politician.objects.bulk_update(update_list, ['profile_image_background_color', 'profile_image_background_color_needed'])
                message = \
                    "Politicians updated: {politicians_updated:,}. " \
                    "Politicians without picture URL:  {politicians_not_updated:,}. " \
                    "".format(politicians_updated=politicians_updated, politicians_not_updated=politicians_not_updated)
                messages.add_message(request, messages.INFO, message)
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                "ERROR with update_profile_image_background_color_view: {e}"
                                "".format(e=e))
    
    # Create seo_friendly_path for all politicians who currently don't have one
    generate_seo_friendly_path_updates = True  # Set False on local machine for now
    number_to_create = 1000
    if generate_seo_friendly_path_updates and run_scripts:
        politician_query = Politician.objects.all()
        politician_query = politician_query.filter(
            Q(seo_friendly_path__isnull=True) |
            Q(seo_friendly_path="")
        )
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_create if total_to_convert > number_to_create else 0
        politician_list_to_convert = list(politician_query[:number_to_create])
        politician_manager = PoliticianManager()
        update_list = []
        updates_needed = False
        updates_made = 0
        # timezone = pytz.timezone("America/Los_Angeles")
        # datetime_now = timezone.localize(datetime.now())
        datetime_now = generate_localized_datetime_from_obj()[1]
        for one_politician in politician_list_to_convert:
            results = politician_manager.generate_seo_friendly_path(
                politician_name=one_politician.politician_name,
                politician_we_vote_id=one_politician.we_vote_id,
                state_code=one_politician.state_code,
            )
            if results['seo_friendly_path_found']:
                one_politician.seo_friendly_path = results['seo_friendly_path']
                one_politician.seo_friendly_path_date_last_updated = datetime_now
                update_list.append(one_politician)
                updates_needed = True
                updates_made += 1
        if updates_needed:
            try:
                Politician.objects.bulk_update(update_list, ['seo_friendly_path', 'seo_friendly_path_date_last_updated'])
                messages.add_message(request, messages.INFO,
                                     "{updates_made:,} politicians updated with new seo_friendly_path. "
                                     "{total_to_convert_after:,} remaining."
                                     "".format(total_to_convert_after=total_to_convert_after,
                                               updates_made=updates_made))
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     "ERROR with generate_seo_friendly_path_updates: {e} "
                                     "".format(e=e))

    # Create default CampaignX for all politicians who currently don't have one
    generate_campaignx_for_every_politician = True
    number_to_create = 1000
    if generate_campaignx_for_every_politician and run_scripts:
        politician_query = Politician.objects.all()
        politician_query = politician_query.filter(
            Q(linked_campaignx_we_vote_id__isnull=True) |
            Q(linked_campaignx_we_vote_id="")
        )
        politician_query = politician_query.exclude(
            Q(seo_friendly_path__isnull=True) |
            Q(seo_friendly_path="")
        )
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_create if total_to_convert > number_to_create else 0
        politician_list_to_convert = list(politician_query[:number_to_create])
        update_list = []
        updates_needed = False
        updates_made = 0
        # timezone = pytz.timezone("America/Los_Angeles")
        # datetime_now = timezone.localize(datetime.now())
        datetime_now = generate_localized_datetime_from_obj()[1]
        for one_politician in politician_list_to_convert:
            results = generate_campaignx_for_politician(
                datetime_now=datetime_now,
                politician=one_politician,
                save_individual_politician=False,
            )
            if results['success'] and results['campaignx_created']:
                one_politician = results['politician']
                update_list.append(one_politician)
                updates_needed = True
                updates_made += 1

        if updates_needed:
            try:
                Politician.objects.bulk_update(
                    update_list, ['linked_campaignx_we_vote_id', 'linked_campaignx_we_vote_id_date_last_updated'])
                messages.add_message(request, messages.INFO,
                                     "Generated CampaignX for {updates_made:,} politicians. "
                                     "{total_to_convert_after:,} remaining."
                                     "".format(total_to_convert_after=total_to_convert_after,
                                               updates_made=updates_made))
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     "ERROR with generate_campaignx_for_every_politician: {e} "
                                     "".format(e=e))

    # Find all politicians with linked_campaignx_we_vote_id and make sure Campaignx
    # entry includes linked_politician_we_vote_id
    # We don't want to always leave this on
    update_campaignx_with_linked_politician_we_vote_id = True
    number_to_update = 7000  # We have to run this routine on the entire state
    if update_campaignx_with_linked_politician_we_vote_id and positive_value_exists(state_code) and run_scripts:
        update_campaignx_with_linked_politician_we_vote_id_status = ""
        politician_query = Politician.objects.all()
        politician_query = politician_query.filter(linked_campaignx_we_vote_id__isnull=False)
        politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        politician_list_to_convert = list(politician_query[:number_to_update])
        campaignx_we_vote_id_list = []
        politician_dict_by_campaign_we_vote_id = {}
        politicians_with_linked_campaignx_we_vote_id_count = 0
        for one_politician in politician_list_to_convert:
            if positive_value_exists(one_politician.linked_campaignx_we_vote_id):
                politicians_with_linked_campaignx_we_vote_id_count += 1
                if one_politician.linked_campaignx_we_vote_id not in campaignx_we_vote_id_list:
                    campaignx_we_vote_id_list.append(one_politician.linked_campaignx_we_vote_id)
                    politician_dict_by_campaign_we_vote_id[one_politician.linked_campaignx_we_vote_id] = one_politician

        update_list = []
        updates_needed = False
        updates_made = 0

        from campaign.models import CampaignX
        campaignx_query = CampaignX.objects.all()
        campaignx_query = campaignx_query.filter(we_vote_id__in=campaignx_we_vote_id_list)
        campaignx_list = list(campaignx_query)
        campaignx_with_linked_politician_we_vote_id_count = 0
        for one_campaignx in campaignx_list:
            if one_campaignx.we_vote_id in politician_dict_by_campaign_we_vote_id:
                one_politician = politician_dict_by_campaign_we_vote_id[one_campaignx.we_vote_id]
                if hasattr(one_politician, 'we_vote_id') and positive_value_exists(one_politician.we_vote_id):
                    if one_campaignx.linked_politician_we_vote_id != one_politician.we_vote_id:
                        one_campaignx.linked_politician_we_vote_id = one_politician.we_vote_id
                        update_list.append(one_campaignx)
                        updates_made += 1
                        if not updates_needed:
                            updates_needed = True

            if positive_value_exists(one_campaignx.linked_politician_we_vote_id):
                campaignx_with_linked_politician_we_vote_id_count += 1

        updates_error = False
        if updates_needed:
            try:
                CampaignX.objects.bulk_update(
                    update_list, ['linked_politician_we_vote_id'])
                update_campaignx_with_linked_politician_we_vote_id_status += \
                    "UPDATES MADE: {updates_made:,} politicians updated with new linked_campaignx_we_vote_id. " \
                    "{total_to_convert_after:,} remaining." \
                    "".format(
                        total_to_convert_after=total_to_convert_after,
                        updates_made=updates_made)
            except Exception as e:
                updates_error = True
                update_campaignx_with_linked_politician_we_vote_id_status += \
                    "ERROR with update_campaignx_with_linked_politician_we_vote_id: {e} " \
                    "".format(e=e)
        elif positive_value_exists(campaignx_with_linked_politician_we_vote_id_count):
            update_campaignx_with_linked_politician_we_vote_id_status += \
                "NO UPDATES: {campaignx_with_linked_politician_we_vote_id_count} CampaignX entries " \
                "already have linked_politician_we_vote_id. " \
                "".format(
                    campaignx_with_linked_politician_we_vote_id_count=campaignx_with_linked_politician_we_vote_id_count)
        if positive_value_exists(update_campaignx_with_linked_politician_we_vote_id_status):
            update_campaignx_with_linked_politician_we_vote_id_status = \
                update_campaignx_with_linked_politician_we_vote_id_status + \
                " (SCRIPT update_campaignx_with_linked_politician_we_vote_id) "

            message_type = messages.ERROR if updates_error else messages.INFO
            messages.add_message(request, message_type, update_campaignx_with_linked_politician_we_vote_id_status)

    politician_list = []
    politician_list_count = 0
    try:
        politician_query = Politician.objects.using('readonly').all()
        if positive_value_exists(show_battleground):
            year_filters = []
            for year_integer in IS_BATTLEGROUND_YEARS_AVAILABLE:
                if positive_value_exists(year_integer):
                    is_battleground_race_key = 'is_battleground_race_' + str(year_integer)
                    one_year_filter = Q(**{is_battleground_race_key: True})
                    year_filters.append(one_year_filter)
            if len(year_filters) > 0:
                # Add the first query
                final_filters = year_filters.pop()
                # ...and "OR" the remaining items in the list
                for item in year_filters:
                    final_filters |= item
                politician_query = politician_query.filter(final_filters)
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        if positive_value_exists(show_politicians_with_email):
            politician_query = \
                politician_query.annotate(politician_email_address_length=Length('politician_email_address'))
            politician_query = politician_query.annotate(politician_email_length=Length('politician_email'))
            politician_query = politician_query.annotate(politician_email2_length=Length('politician_email2'))
            politician_query = politician_query.annotate(politician_email3_length=Length('politician_email3'))
            politician_query = politician_query.filter(
                Q(politician_email_address_length__gt=2) |
                Q(politician_email_length__gt=2) |
                Q(politician_email2_length__gt=2) |
                Q(politician_email3_length__gt=2)
            )
        if positive_value_exists(show_ocd_id_state_mismatch):
            politician_query = politician_query.filter(ocd_id_state_mismatch_found=True)

        if positive_value_exists(politician_search):
            search_words = politician_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(first_name__iexact=one_word)
                filters.append(new_filter)

                new_filter = (
                    Q(google_civic_candidate_name__icontains=one_word) |
                    Q(google_civic_candidate_name2__icontains=one_word) |
                    Q(google_civic_candidate_name3__icontains=one_word)
                )
                filters.append(new_filter)

                new_filter = Q(last_name__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(linked_campaignx_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = (
                    Q(politician_email__icontains=one_word) |
                    Q(politician_email2__icontains=one_word) |
                    Q(politician_email3__icontains=one_word)
                )
                filters.append(new_filter)

                new_filter = Q(politician_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = (
                    Q(politician_twitter_handle__icontains=one_word) |
                    Q(politician_twitter_handle2__icontains=one_word) |
                    Q(politician_twitter_handle3__icontains=one_word) |
                    Q(politician_twitter_handle4__icontains=one_word) |
                    Q(politician_twitter_handle5__icontains=one_word)
                )
                filters.append(new_filter)

                new_filter = Q(political_party__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(seo_friendly_path__icontains=one_word)
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

                    politician_query = politician_query.filter(final_filters)

        politician_list_count = politician_query.count()
        if not positive_value_exists(show_all):
            politician_list = politician_query.order_by('politician_name')[:25]
        else:
            # We still want to limit to 200
            politician_list = politician_query.order_by('politician_name')[:200]
    except ObjectDoesNotExist:
        # This is fine
        pass

    # Attach candidates linked to these politicians
    temp_politician_list = []
    for one_politician in politician_list:
        try:
            linked_candidate_query = CandidateCampaign.objects.using('readonly').all()
            linked_candidate_query = linked_candidate_query.filter(
                Q(politician_we_vote_id__iexact=one_politician.we_vote_id) |
                Q(politician_id=one_politician.id))
            linked_candidate_list_count = linked_candidate_query.count()
            one_politician.linked_candidate_list_count = linked_candidate_list_count
            temp_politician_list.append(one_politician)
        except Exception as e:
            pass

    politician_list = temp_politician_list

    # Cycle through all Politicians and find unlinked Candidates that *might* be "children" of this politician
    if show_related_candidates:
        temp_politician_list = []
        for one_politician in politician_list:
            try:
                related_candidate_list = CandidateCampaign.objects.using('readonly').all()
                related_candidate_list = related_candidate_list.exclude(politician_we_vote_id=one_politician.we_vote_id)

                filters = []
                new_filter = Q(candidate_name__icontains=one_politician.first_name) & \
                    Q(candidate_name__icontains=one_politician.last_name)
                filters.append(new_filter)

                if positive_value_exists(one_politician.politician_twitter_handle):
                    new_filter = (
                        Q(candidate_twitter_handle__iexact=one_politician.politician_twitter_handle) |
                        Q(candidate_twitter_handle2__iexact=one_politician.politician_twitter_handle) |
                        Q(candidate_twitter_handle3__iexact=one_politician.politician_twitter_handle)
                    )
                    filters.append(new_filter)

                if positive_value_exists(one_politician.politician_twitter_handle2):
                    new_filter = (
                        Q(candidate_twitter_handle__iexact=one_politician.politician_twitter_handle2) |
                        Q(candidate_twitter_handle2__iexact=one_politician.politician_twitter_handle2) |
                        Q(candidate_twitter_handle3__iexact=one_politician.politician_twitter_handle2)
                    )
                    filters.append(new_filter)

                if positive_value_exists(one_politician.politician_twitter_handle3):
                    new_filter = (
                        Q(candidate_twitter_handle__iexact=one_politician.politician_twitter_handle3) |
                        Q(candidate_twitter_handle2__iexact=one_politician.politician_twitter_handle3) |
                        Q(candidate_twitter_handle3__iexact=one_politician.politician_twitter_handle3)
                    )
                    filters.append(new_filter)

                if positive_value_exists(one_politician.politician_twitter_handle4):
                    new_filter = (
                        Q(candidate_twitter_handle__iexact=one_politician.politician_twitter_handle4) |
                        Q(candidate_twitter_handle2__iexact=one_politician.politician_twitter_handle4) |
                        Q(candidate_twitter_handle3__iexact=one_politician.politician_twitter_handle4)
                    )
                    filters.append(new_filter)

                if positive_value_exists(one_politician.politician_twitter_handle5):
                    new_filter = (
                        Q(candidate_twitter_handle__iexact=one_politician.politician_twitter_handle5) |
                        Q(candidate_twitter_handle2__iexact=one_politician.politician_twitter_handle5) |
                        Q(candidate_twitter_handle3__iexact=one_politician.politician_twitter_handle5)
                    )
                    filters.append(new_filter)

                if positive_value_exists(one_politician.vote_smart_id):
                    new_filter = Q(vote_smart_id=one_politician.vote_smart_id)
                    filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    related_candidate_list = related_candidate_list.filter(final_filters)

                related_candidate_list_count = related_candidate_list.count()
            except Exception as e:
                related_candidate_list_count = 0

            one_politician.related_candidate_list_count = related_candidate_list_count
            temp_politician_list.append(one_politician)

        politician_list = temp_politician_list

    # Now find all representative ids related to this politician
    temp_politician_list = []
    for one_politician in politician_list:
        if one_politician.we_vote_id:
            try:
                queryset = Representative.objects.all()
                queryset = queryset.filter(politician_we_vote_id__iexact=one_politician.we_vote_id)
                linked_representative_we_vote_id_list = []
                linked_representative_list = list(queryset)
                if positive_value_exists(show_ocd_id_state_mismatch):
                    one_politician.linked_representative_list = []
                for representative in linked_representative_list:
                    linked_representative_we_vote_id_list.append(representative.we_vote_id)
                    if positive_value_exists(show_ocd_id_state_mismatch):
                        one_politician.linked_representative_list.append(representative)
                one_politician.linked_representative_we_vote_id_list = linked_representative_we_vote_id_list
            except Exception as e:
                related_candidate_list_count = 0

        temp_politician_list.append(one_politician)

    politician_list = temp_politician_list

    election_list = Election.objects.order_by('-election_day_text')

    messages.add_message(request, messages.INFO,
                         "Politician Count: {politician_list_count:,}"
                         "".format(politician_list_count=politician_list_count))

    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
    template_values = {
        'messages_on_stage':            messages_on_stage,
        'google_civic_election_id':     google_civic_election_id,
        'politician_list':              politician_list,
        'politician_search':            politician_search,
        'election_list':                election_list,
        'show_all':                     show_all,
        'show_battleground':            show_battleground,
        'show_politicians_with_email':  show_politicians_with_email,
        'show_related_candidates':      show_related_candidates,
        'show_ocd_id_state_mismatch':   show_ocd_id_state_mismatch,
        'state_code':                   state_code,
        'state_list':                   sorted_state_list,
        'web_app_root_url':             web_app_root_url,
    }
    return render(request, 'politician/politician_list.html', template_values)


@login_required
def politician_merge_process_view(request):
    """
    Process the merging of two politicians
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ''
    politician_manager = PoliticianManager()

    merge = request.POST.get('merge', False)
    skip = request.POST.get('skip', False)

    # Politician 1 is the one we keep, and Politician 2 is the one we will merge into Politician 1
    politician1_we_vote_id = request.POST.get('politician1_we_vote_id', 0)
    politician2_we_vote_id = request.POST.get('politician2_we_vote_id', 0)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    # redirect_to_politician_list = request.POST.get('redirect_to_politician_list', False)
    # remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    state_code = request.POST.get('state_code', '')
    volunteer_task_manager = VolunteerTaskManager()
    voter_device_id = get_voter_api_device_id(request)
    voter_id = 0
    voter_we_vote_id = ''
    if positive_value_exists(voter_device_id):
        voter = fetch_voter_from_voter_device_link(voter_device_id)
        if hasattr(voter, 'we_vote_id'):
            voter_id = voter.id
            voter_we_vote_id = voter.we_vote_id

    if positive_value_exists(skip):
        results = politician_manager.update_or_create_politicians_are_not_duplicates(
            politician1_we_vote_id, politician2_we_vote_id)
        if results['success']:
            queryset = PoliticiansArePossibleDuplicates.objects.filter(
                politician1_we_vote_id__iexact=politician1_we_vote_id,
                politician2_we_vote_id__iexact=politician2_we_vote_id,
            )
            queryset.delete()
            messages.add_message(request, messages.INFO, 'Prior politicians skipped, and not merged.')
            if positive_value_exists(voter_we_vote_id):
                try:
                    # Give the volunteer who entered this credit
                    task_results = volunteer_task_manager.create_volunteer_task_completed(
                        action_constant=VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION,
                        voter_id=voter_id,
                        voter_we_vote_id=voter_we_vote_id,
                    )
                except Exception as e:
                    status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED-DEDUPLICATION: ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        else:
            messages.add_message(request, messages.ERROR,
                                 'ERROR update_or_create_politicians_are_not_duplicates: ' +
                                 results['status'])
        return HttpResponseRedirect(reverse('politician:duplicates_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    politician1_results = politician_manager.retrieve_politician(
        politician_we_vote_id=politician1_we_vote_id,
        read_only=True)
    if politician1_results['politician_found']:
        politician1_on_stage = politician1_results['politician']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve politician 1.')
        return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    politician2_results = politician_manager.retrieve_politician_from_we_vote_id(politician2_we_vote_id)
    if politician2_results['politician_found']:
        politician2_on_stage = politician2_results['politician']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve politician 2.')
        return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    # Gather choices made from merge form
    conflict_results = figure_out_politician_conflict_values(politician1_on_stage, politician2_on_stage)
    politician_merge_conflict_values = conflict_results['politician_merge_conflict_values']
    if not conflict_results['success']:
        status += conflict_results['status']
        messages.add_message(request, messages.ERROR, status)
    admin_merge_choices = {}
    clear_these_attributes_from_politician2 = []
    for attribute in POLITICIAN_UNIQUE_IDENTIFIERS:
        conflict_value = politician_merge_conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            choice = request.POST.get(attribute + '_choice', '')
            if politician2_we_vote_id == choice:
                admin_merge_choices[attribute] = getattr(politician2_on_stage, attribute)
            if attribute in POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                clear_these_attributes_from_politician2.append(attribute)
        elif conflict_value == "POLITICIAN2":
            admin_merge_choices[attribute] = getattr(politician2_on_stage, attribute)
            if attribute in POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                clear_these_attributes_from_politician2.append(attribute)

    merge_results = merge_these_two_politicians(
        politician1_we_vote_id,
        politician2_we_vote_id,
        admin_merge_choices,
        clear_these_attributes_from_politician2)

    if positive_value_exists(merge_results['politicians_merged']):
        politician = merge_results['politician']
        messages.add_message(request, messages.INFO, "Politician '{politician_name}' merged."
                                                     "".format(politician_name=politician.politician_name))
        queryset = PoliticiansArePossibleDuplicates.objects.filter(
            politician1_we_vote_id__iexact=politician1_we_vote_id,
            politician2_we_vote_id__iexact=politician2_we_vote_id,
        )
        queryset.delete()
        if positive_value_exists(voter_we_vote_id):
            try:
                # Give the volunteer who entered this credit
                task_results = volunteer_task_manager.create_volunteer_task_completed(
                    action_constant=VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION,
                    voter_id=voter_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
            except Exception as e:
                status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED-DEDUPLICATION: ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician1_on_stage.id,)))

    else:
        messages.add_message(request, messages.ERROR, merge_results['status'])
        return HttpResponseRedirect(reverse('politician:duplicates_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # if redirect_to_politician_list:
    #     return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
    #                                 '?google_civic_election_id=' + str(google_civic_election_id) +
    #                                 '&state_code=' + str(state_code))
    #
    # if remove_duplicate_process:
    #     return HttpResponseRedirect(reverse('politician:find_and_merge_duplicate_politicians', args=()) +
    #                                 "?google_civic_election_id=" + str(google_civic_election_id) +
    #                                 "&state_code=" + str(state_code))
    #
    # return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician1_on_stage.id,)))


@login_required
def politician_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    contest_office_id = request.GET.get('contest_office_id', 0)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    politician_name = request.GET.get('politician_name', "")
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', "")
    google_civic_candidate_name2 = request.GET.get('google_civic_candidate_name2', "")
    google_civic_candidate_name3 = request.GET.get('google_civic_candidate_name3', "")
    state_code = request.GET.get('state_code', "")
    politician_twitter_handle = request.GET.get('politician_twitter_handle', "")
    politician_twitter_handle2 = request.GET.get('politician_twitter_handle2', "")
    politician_twitter_handle3 = request.GET.get('politician_twitter_handle3', "")
    politician_twitter_handle4 = request.GET.get('politician_twitter_handle4', "")
    politician_twitter_handle5 = request.GET.get('politician_twitter_handle5', "")
    politician_url = request.GET.get('politician_url', "")
    politician_url2 = request.GET.get('politician_url2', "")
    politician_url3 = request.GET.get('politician_url3', "")
    politician_url4 = request.GET.get('politician_url4', "")
    politician_url5 = request.GET.get('politician_url5', "")
    political_party = request.GET.get('political_party', "")
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', "")
    vote_smart_id = request.GET.get('vote_smart_id', "")
    maplight_id = request.GET.get('maplight_id', "")
    politician_we_vote_id = request.GET.get('politician_we_vote_id', "")
    gender = request.GET.get('gender', "U")
    gender_likelihood = request.GET.get('gender_likelihood', "")
    ballotpedia_politician_name = request.GET.get('ballotpedia_politician_name', "")
    birth_date = request.GET.get('birth_date', "")
    first_name = request.GET.get('first_name', "")
    last_name = request.GET.get('last_name', "")
    middle_name = request.GET.get('middle_name', "")
    politician_email = request.GET.get('politician_email', "")
    politician_email2 = request.GET.get('politician_email2', "")
    politician_email3 = request.GET.get('politician_email3', "")
    politician_phone_number = request.GET.get('politician_phone_number', "")
    politician_phone_number2 = request.GET.get('politician_phone_number2', "")
    politician_phone_number3 = request.GET.get('politician_phone_number3', "")
    vote_usa_politician_id = request.GET.get('vote_usa_politician_id', "")
    youtube_url = request.GET.get('youtube_url', "")

    # These are the Offices already entered for this election
    try:
        contest_office_list = ContestOffice.objects.order_by('office_name')
        contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        contest_office_list = []

    # It's helpful to see existing politicians when entering a new politician
    politician_list = []
    try:
        politician_list = Politician.objects.all()
        if positive_value_exists(google_civic_election_id):
            politician_list = politician_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(contest_office_id):
            politician_list = politician_list.filter(contest_office_id=contest_office_id)
        politician_list = politician_list.order_by('politician_name')[:500]
    except Politician.DoesNotExist:
        # This is fine, create new
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':                messages_on_stage,
        'office_list':                      contest_office_list,
        'contest_office_id':                contest_office_id,  # Pass in separately for the template to work
        'gender':                           gender,
        'gender_likelihood':                gender_likelihood,
        'google_civic_election_id':         google_civic_election_id,
        'politician_list':                  politician_list,
        # Incoming variables, not saved yet
        'politician_name':                  politician_name,
        'google_civic_candidate_name':      google_civic_candidate_name,
        'google_civic_candidate_name2':     google_civic_candidate_name2,
        'google_civic_candidate_name3':     google_civic_candidate_name3,
        'state_code':                       state_code,
        'politician_twitter_handle':        politician_twitter_handle,
        'politician_twitter_handle2':       politician_twitter_handle2,
        'politician_twitter_handle3':       politician_twitter_handle3,
        'politician_twitter_handle4':       politician_twitter_handle4,
        'politician_twitter_handle5':       politician_twitter_handle5,
        'politician_url':                   politician_url,
        'politician_url2':                  politician_url2,
        'politician_url3':                  politician_url3,
        'politician_url4':                  politician_url4,
        'politician_url5':                  politician_url5,
        'political_party':                  political_party,
        'ballot_guide_official_statement':  ballot_guide_official_statement,
        'vote_smart_id':                    vote_smart_id,
        'maplight_id':                      maplight_id,
        'politician_we_vote_id':            politician_we_vote_id,
        'ballotpedia_politician_name_dict':
        {
            'label':    'Name from Ballotpedia',
            'id':       'ballotpedia_politician_name_id',
            'name':     'ballotpedia_politician_name',
            'value':     ballotpedia_politician_name
        },
        'birth_date_dict':
        {
        'label':    'Birthdate (format Feb. 16, 1955)',
        'id':       'birth_date_id',
        'name':     'birth_date',
            'value':     birth_date
        },
        'first_name_dict':
        {
            'label':    'First Name',
            'id':       'first_name_id',
            'name':     'first_name',
            'value':     first_name
        },
        'last_name_dict':
        {
            'label':    'Last Name',
            'id':       'last_name_id',
            'name':     'last_name',
            'value':     last_name
        },
        'middle_name_dict':
        {
            'label':    'Middle Name',
            'id':       'middle_name_id',
            'name':     'middle_name',
            'value':     middle_name
        },
        'google_civic_candidate_name_dict':
        {
            'label':    'Politician Name (for Google Civic matching)',
            'id':       'google_civic_candidate_name_id',
            'name':     'google_civic_candidate_name',
            'value':     google_civic_candidate_name
        },
        'google_civic_candidate_name2_dict':
        {
            'label':    'Politician Name 2',
            'id':       'google_civic_candidate_name2_id',
            'name':     'google_civic_candidate_name2',
            'value':     google_civic_candidate_name2
        },
        'google_civic_candidate_name3_dict':
        {
            'label':    'Politician Name 3',
            'id':       'google_civic_candidate_name3_id',
            'name':     'google_civic_candidate_name3',
            'value':     google_civic_candidate_name3
        },
        'maplight_id_dict':
        {
            'label':    'MapLight Id',
            'id':       'maplight_id_id',
            'name':     'maplight_id',
            'value':     maplight_id
        },
        'politician_email_dict':
        {
            'label':    'Politician Email',
            'id':       'politician_email_id',
            'name':     'politician_email',
            'value':     politician_email
        },
        'politician_email2_dict':
        {
            'label':    'Email 2',
            'id':       'politician_email2_id',
            'name':     'politician_email2',
            'value':     politician_email2
        },
        'politician_email3_dict':
        {
            'label':    'Email 3',
            'id':       'politician_email3_id',
            'name':     'politician_email3',
            'value':     politician_email3
        },
        'politician_phone_number_dict':
        {
            'label':    'Politician Phone',
            'id':       'politician_phone_number_id',
            'name':     'politician_phone_number',
            'value':     politician_phone_number
        },
        'politician_phone_number2_dict':
        {
            'label':    'Phone 2',
            'id':       'politician_phone_number2_id',
            'name':     'politician_phone_number2',
            'value':     politician_phone_number2
        },
        'politician_phone_number3_dict':
        {
            'label':    'Phone 3',
            'id':       'politician_phone_number3_id',
            'name':     'politician_phone_number3',
            'value':     politician_phone_number3
        },
        'political_party_dict':
        {
            'label':    'Politician Party',
            'id':       'political_party_id',
            'name':     'political_party',
            'value':     political_party
        },
        'state_code_dict':
        {
            'label':    'State Code',
            'id':       'state_code_id',
            'name':     'state_code',
            'value':     state_code
        },
        'vote_smart_id_dict':
        {
            'label':    'Vote Smart Id',
            'id':       'vote_smart_id_id',
            'name':     'vote_smart_id',
            'value':     vote_smart_id
        },
        'vote_usa_politician_id_dict':
        {
            'label':    'Vote USA Politician Id',
            'id':       'vote_usa_politician_id_id',
            'name':     'vote_usa_politician_id',
            'value':     vote_usa_politician_id
        },
        'youtube_url_dict':
        {
            'label':    'YouTube URL',
            'id':       'youtube_url_id',
            'name':     'youtube_url',
            'value':     youtube_url
        },
    }
    return render(request, 'politician/politician_edit.html', template_values)


@login_required
def politician_delete_all_duplicates_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    if positive_value_exists(state_code):
        queryset = PoliticiansArePossibleDuplicates.objects.filter(
            state_code__iexact=state_code,
        )
        queryset.delete()
        messages.add_message(request, messages.INFO, 'Duplicate politician data deleted.')
    else:
        messages.add_message(request, messages.INFO, 'Duplicate politician data NOT deleted. State code missing.')
    return HttpResponseRedirect(reverse('politician:duplicates_list', args=()) +
                                "?state_code=" + str(state_code))


@login_required
def politician_duplicates_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    politician_search = request.GET.get('politician_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all = positive_value_exists(request.GET.get('show_all', False))
    show_related_candidates = positive_value_exists(request.GET.get('show_related_candidates', False))
    show_politicians_with_email = request.GET.get('show_politicians_with_email', False)

    duplicates_list = []
    duplicates_list_count = 0
    possible_duplicates_count = 0
    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        queryset = PoliticiansArePossibleDuplicates.objects.using('readonly').all()
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        duplicates_list_count = queryset.count()
        queryset = queryset.exclude(
            Q(politician2_we_vote_id__isnull=True) | Q(politician2_we_vote_id=''))
        possible_duplicates_count = queryset.count()
        if not positive_value_exists(show_all):
            duplicates_list = list(queryset[:200])
        else:
            duplicates_list = list(queryset[:1000])
    except ObjectDoesNotExist:
        # This is fine
        pass

    politicians_dict = {}
    politicians_to_display_we_vote_id_list = []
    for one_duplicate in duplicates_list:
        if positive_value_exists(one_duplicate.politician1_we_vote_id):
            politicians_to_display_we_vote_id_list.append(one_duplicate.politician1_we_vote_id)
        if positive_value_exists(one_duplicate.politician2_we_vote_id):
            politicians_to_display_we_vote_id_list.append(one_duplicate.politician2_we_vote_id)
    try:
        queryset = Politician.objects.using('readonly').all()
        queryset = queryset.filter(we_vote_id__in=politicians_to_display_we_vote_id_list)
        politician_data_list = list(queryset)
        for one_politician in politician_data_list:
            politicians_dict[one_politician.we_vote_id] = one_politician
    except Exception as e:
        pass

    duplicates_list_modified = []
    for one_duplicate in duplicates_list:
        if positive_value_exists(one_duplicate.politician1_we_vote_id) \
                and one_duplicate.politician1_we_vote_id in politicians_dict \
                and positive_value_exists(one_duplicate.politician2_we_vote_id) \
                and one_duplicate.politician2_we_vote_id in politicians_dict:
            one_duplicate.politician1 = politicians_dict[one_duplicate.politician1_we_vote_id]
            one_duplicate.politician2 = politicians_dict[one_duplicate.politician2_we_vote_id]
            duplicates_list_modified.append(one_duplicate)
        else:
            possible_duplicates_count -= 1

    messages.add_message(request, messages.INFO,
                         "Politicians analyzed: {duplicates_list_count:,}. "
                         "Possible duplicate politicians found: {possible_duplicates_count:,}. "
                         "State: {state_code}"
                         "".format(
                             duplicates_list_count=duplicates_list_count,
                             possible_duplicates_count=possible_duplicates_count,
                             state_code=state_code))

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'google_civic_election_id':     google_civic_election_id,
        'duplicates_list':              duplicates_list_modified,
        'politician_search':            politician_search,
        'show_all':                     show_all,
        'show_politicians_with_email':  show_politicians_with_email,
        'show_related_candidates':      show_related_candidates,
        'state_code':                   state_code,
        'state_list':                   sorted_state_list,
    }
    return render(request, 'politician/politician_duplicates_list.html', template_values)


@login_required
def politician_edit_by_we_vote_id_view(request, politician_we_vote_id):
    politician_manager = PoliticianManager()
    politician_id = politician_manager.fetch_politician_id_from_we_vote_id(politician_we_vote_id)
    return politician_we_vote_id(request, politician_id)


@login_required
def politician_edit_view(request, politician_id=0, politician_we_vote_id=''):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    ballotpedia_politician_url = request.GET.get('ballotpedia_politician_url', False)
    birth_date = request.GET.get('birth_date', False)
    ballotpedia_politician_name = request.GET.get('ballotpedia_politician_name', False)
    facebook_url = request.GET.get('facebook_url', False)
    facebook_url2 = request.GET.get('facebook_url2', False)
    facebook_url3 = request.GET.get('facebook_url3', False)
    first_name = request.GET.get('first_name', False)
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', False)
    google_civic_candidate_name2 = request.GET.get('google_civic_candidate_name2', False)
    google_civic_candidate_name3 = request.GET.get('google_civic_candidate_name3', False)
    instagram_handle = request.GET.get('instagram_handle', False)
    if positive_value_exists(instagram_handle):
        instagram_handle = extract_instagram_handle_from_text_string(instagram_handle)
    last_name = request.GET.get('last_name', False)
    middle_name = request.GET.get('middle_name', False)
    politician_contact_form_url = request.GET.get('politician_contact_form_url', False)
    politician_email = request.GET.get('politician_email', False)
    politician_email2 = request.GET.get('politician_email2', False)
    politician_email3 = request.GET.get('politician_email3', False)
    politician_name = request.GET.get('politician_name', False)
    politician_phone_number = request.GET.get('politician_phone_number', False)
    politician_phone_number2 = request.GET.get('politician_phone_number2', False)
    politician_phone_number3 = request.GET.get('politician_phone_number3', False)
    politician_twitter_handle = request.GET.get('politician_twitter_handle', False)
    politician_twitter_handle2 = request.GET.get('politician_twitter_handle2', False)
    politician_twitter_handle3 = request.GET.get('politician_twitter_handle3', False)
    politician_twitter_handle4 = request.GET.get('politician_twitter_handle4', False)
    politician_twitter_handle5 = request.GET.get('politician_twitter_handle5', False)
    politician_url = request.GET.get('politician_url', False)
    politician_url2 = request.GET.get('politician_url2', False)
    politician_url3 = request.GET.get('politician_url3', False)
    politician_url4 = request.GET.get('politician_url4', False)
    politician_url5 = request.GET.get('politician_url5', False)
    political_party = request.GET.get('political_party', False)
    state_code = request.GET.get('state_code', False)
    status = ''
    vote_smart_id = request.GET.get('vote_smart_id', False)
    vote_usa_politician_id = request.GET.get('vote_usa_politician_id', False)
    youtube_url = request.GET.get('youtube_url', False)
    maplight_id = request.GET.get('maplight_id', False)

    messages_on_stage = get_messages(request)
    politician_id = convert_to_int(politician_id)
    politician_on_stage_found = False
    politician_on_stage = Politician()

    try:
        if positive_value_exists(politician_id):
            politician_on_stage = Politician.objects.get(id=politician_id)
            politician_we_vote_id = politician_on_stage.we_vote_id
        else:
            politician_on_stage = Politician.objects.get(we_vote_id=politician_we_vote_id)
            politician_id = politician_on_stage.id
        politician_on_stage_found = True
    except Politician.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Politician.DoesNotExist:
        # This is fine, create new below
        pass

    if politician_on_stage_found:
        # Generate a CampaignX entry for this politician if one does not exist
        if not positive_value_exists(politician_on_stage.linked_campaignx_we_vote_id):
            results = generate_campaignx_for_politician(
                politician=politician_on_stage,
                save_individual_politician=True,
            )
            politician_on_stage = results['politician']

        # Working with Vote Smart data
        rating_list = []
        vote_smart_turned_on = False
        if vote_smart_turned_on:
            try:
                vote_smart_politician_id = politician_on_stage.vote_smart_id
                rating_list_query = VoteSmartRatingOneCandidate.objects.order_by('-timeSpan')  # Desc order
                rating_list = rating_list_query.filter(candidateId=vote_smart_politician_id)
            except VotesmartApiError as error_instance:
                # Catch the error message coming back from Vote Smart and pass it in the status
                error_message = error_instance.args
                status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
                print_to_log(logger=logger, exception_message_optional=status)
                rating_list = []

        # ##################################
        # Show the seo friendly paths for this politician
        path_count = 0
        path_list = []
        if positive_value_exists(politician_we_vote_id):
            from politician.models import PoliticianSEOFriendlyPath
            try:
                path_query = PoliticianSEOFriendlyPath.objects.all()
                path_query = path_query.filter(politician_we_vote_id__iexact=politician_we_vote_id)
                path_count = path_query.count()
                path_list = list(path_query[:4])
            except Exception as e:
                status += 'ERROR_RETRIEVING_FROM_PoliticianSEOFriendlyPath: ' + str(e) + ' '

            if positive_value_exists(politician_on_stage.seo_friendly_path):
                path_list_modified = []
                for one_path in path_list:
                    if politician_on_stage.seo_friendly_path != one_path.final_pathname_string:
                        path_list_modified.append(one_path)
                path_list = path_list_modified
            path_list = path_list[:3]

        # Working with We Vote Positions
        try:
            politician_position_query = PositionEntered.objects.order_by('stance')
            # As of Aug 2018 we are no longer using PERCENT_RATING
            politician_position_query = politician_position_query.exclude(stance__iexact='PERCENT_RATING')
            politician_position_list = politician_position_query.filter(
                politician_we_vote_id__iexact=politician_on_stage.we_vote_id)
        except Exception as e:
            politician_position_list = []

        # ##################################
        # Find Candidate "children" of this politician
        try:
            linked_candidate_list = CandidateCampaign.objects.all()
            linked_candidate_list = linked_candidate_list.filter(
                Q(politician_we_vote_id__iexact=politician_on_stage.we_vote_id) |
                Q(politician_id=politician_on_stage.id))
        except Exception as e:
            linked_candidate_list = []

        linked_candidate_we_vote_id_list = []
        for candidate in linked_candidate_list:
            linked_candidate_we_vote_id_list.append(candidate.we_vote_id)
        if len(linked_candidate_we_vote_id_list) > 0:
            try:
                queryset = CandidateToOfficeLink.objects.all()
                queryset = queryset.filter(candidate_we_vote_id__in=linked_candidate_we_vote_id_list)
                candidate_to_office_link_list = list(queryset)
            except Exception as e:
                candidate_to_office_link_list = []
            if len(candidate_to_office_link_list) > 0:
                modified_linked_candidate_list = []
                for one_candidate in linked_candidate_list:
                    one_candidate.contest_office_we_vote_id_list = []  # Add new variable for template display purposes
                    for candidate_to_office_link in candidate_to_office_link_list:
                        if candidate_to_office_link.candidate_we_vote_id == one_candidate.we_vote_id:
                            one_candidate.contest_office_we_vote_id_list\
                                .append(candidate_to_office_link.contest_office_we_vote_id)
                    modified_linked_candidate_list.append(one_candidate)
                linked_candidate_list = modified_linked_candidate_list

        # ##################################
        # Find Candidates to Link to this Politician
        # Finding Candidates that *might* be "children" of this politician
        from politician.controllers import find_candidates_to_link_to_this_politician
        related_candidate_list = find_candidates_to_link_to_this_politician(politician=politician_on_stage)

        # Find possible duplicate politicians
        duplicate_politician_list = []
        if positive_value_exists(politician_on_stage.politician_name) or \
                positive_value_exists(politician_on_stage.first_name) or \
                positive_value_exists(politician_on_stage.last_name) or \
                positive_value_exists(politician_on_stage.politician_twitter_handle) or \
                positive_value_exists(politician_on_stage.vote_smart_id):
            try:
                duplicate_politician_list = Politician.objects.all()
                duplicate_politician_list = duplicate_politician_list.exclude(
                    we_vote_id__iexact=politician_on_stage.we_vote_id)

                filters = []
                if positive_value_exists(politician_on_stage.politician_name):
                    new_filter = Q(politician_name__icontains=politician_on_stage.politician_name)
                    filters.append(new_filter)

                if positive_value_exists(politician_on_stage.first_name) or \
                        positive_value_exists(politician_on_stage.last_name):
                    new_filter = Q(first_name__icontains=politician_on_stage.first_name) & \
                        Q(last_name__icontains=politician_on_stage.last_name)
                    filters.append(new_filter)

                if positive_value_exists(politician_on_stage.politician_twitter_handle):
                    new_filter = (
                        Q(politician_twitter_handle__icontains=politician_on_stage.politician_twitter_handle) |
                        Q(politician_twitter_handle2__icontains=politician_on_stage.politician_twitter_handle) |
                        Q(politician_twitter_handle3__icontains=politician_on_stage.politician_twitter_handle) |
                        Q(politician_twitter_handle4__icontains=politician_on_stage.politician_twitter_handle) |
                        Q(politician_twitter_handle5__icontains=politician_on_stage.politician_twitter_handle)
                    )
                    filters.append(new_filter)

                if positive_value_exists(politician_on_stage.politician_twitter_handle2):
                    new_filter = (
                        Q(politician_twitter_handle__icontains=politician_on_stage.politician_twitter_handle2) |
                        Q(politician_twitter_handle2__icontains=politician_on_stage.politician_twitter_handle2) |
                        Q(politician_twitter_handle3__icontains=politician_on_stage.politician_twitter_handle2) |
                        Q(politician_twitter_handle4__icontains=politician_on_stage.politician_twitter_handle2) |
                        Q(politician_twitter_handle5__icontains=politician_on_stage.politician_twitter_handle2)
                    )
                    filters.append(new_filter)

                if positive_value_exists(politician_on_stage.politician_twitter_handle3):
                    new_filter = (
                        Q(politician_twitter_handle__icontains=politician_on_stage.politician_twitter_handle3) |
                        Q(politician_twitter_handle2__icontains=politician_on_stage.politician_twitter_handle3) |
                        Q(politician_twitter_handle3__icontains=politician_on_stage.politician_twitter_handle3) |
                        Q(politician_twitter_handle4__icontains=politician_on_stage.politician_twitter_handle3) |
                        Q(politician_twitter_handle5__icontains=politician_on_stage.politician_twitter_handle3)
                    )
                    filters.append(new_filter)

                if positive_value_exists(politician_on_stage.politician_twitter_handle4):
                    new_filter = (
                        Q(politician_twitter_handle__icontains=politician_on_stage.politician_twitter_handle4) |
                        Q(politician_twitter_handle2__icontains=politician_on_stage.politician_twitter_handle4) |
                        Q(politician_twitter_handle3__icontains=politician_on_stage.politician_twitter_handle4) |
                        Q(politician_twitter_handle4__icontains=politician_on_stage.politician_twitter_handle4) |
                        Q(politician_twitter_handle5__icontains=politician_on_stage.politician_twitter_handle4)
                    )
                    filters.append(new_filter)

                if positive_value_exists(politician_on_stage.politician_twitter_handle5):
                    new_filter = (
                        Q(politician_twitter_handle__icontains=politician_on_stage.politician_twitter_handle5) |
                        Q(politician_twitter_handle2__icontains=politician_on_stage.politician_twitter_handle5) |
                        Q(politician_twitter_handle3__icontains=politician_on_stage.politician_twitter_handle5) |
                        Q(politician_twitter_handle4__icontains=politician_on_stage.politician_twitter_handle5) |
                        Q(politician_twitter_handle5__icontains=politician_on_stage.politician_twitter_handle5)
                    )
                    filters.append(new_filter)

                if positive_value_exists(politician_on_stage.vote_smart_id):
                    new_filter = Q(vote_smart_id=politician_on_stage.vote_smart_id)
                    filters.append(new_filter)

                politician_on_stage.politician_name_normalized = ''
                if positive_value_exists(politician_on_stage.politician_name):
                    raw = politician_on_stage.politician_name
                    cnt = sum(1 for c in raw if c.isupper())
                    if cnt > 5:
                        humanized = display_full_name_with_correct_capitalization(raw)
                        humanized_cleaned = humanized.replace('(', '').replace(')', '')
                        politician_on_stage.politician_name_normalized = string.capwords(humanized_cleaned)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    duplicate_politician_list = duplicate_politician_list.filter(final_filters)

                duplicate_politician_list = duplicate_politician_list.order_by('politician_name')[:20]
            except ObjectDoesNotExist:
                # This is fine, create new
                pass

        # ##################################
        # Find Representatives Linked to this Politician
        linked_representative_list = []
        if positive_value_exists(politician_we_vote_id):
            queryset = Representative.objects.using('readonly').all()
            queryset = queryset.filter(politician_we_vote_id__iexact=politician_we_vote_id)
            linked_representative_list = list(queryset)

        # ##################################
        # Find Representatives to Link to this Politician
        # Finding Representatives that *might* be "children" of this politician
        from politician.controllers import find_representatives_to_link_to_this_politician
        related_representative_list = find_representatives_to_link_to_this_politician(politician=politician_on_stage)

        # ##################################
        # Find Campaigns Linked to this Politician
        linked_campaignx_list = []
        if positive_value_exists(politician_we_vote_id):
            from campaign.models import CampaignX
            queryset = CampaignX.objects.using('readonly').all()
            queryset = queryset.filter(linked_politician_we_vote_id__iexact=politician_we_vote_id)
            linked_campaignx_list = list(queryset)

        # ##################################
        # Find Campaigns to Link to this Politician
        # Finding Representatives that *might* be "children" of this politician
        from politician.controllers import find_campaignx_list_to_link_to_this_politician
        related_campaignx_list = find_campaignx_list_to_link_to_this_politician(politician=politician_on_stage)

        # ##################################
        # Find Recommendations related to this Politician
        recommended_politicians = []
        if positive_value_exists(politician_we_vote_id):
            from politician.models import RecommendedPoliticianLinkByPolitician
            queryset = RecommendedPoliticianLinkByPolitician.objects.using('readonly').all()
            queryset = queryset.filter(from_politician_we_vote_id__iexact=politician_we_vote_id)
            recommended_politicians = list(queryset)
        recommended_politician_we_vote_ids = [rec.recommended_politician_we_vote_id for rec in recommended_politicians]
        recommended_politicians_list = []
        if recommended_politician_we_vote_ids:
            recommended_politicians_list = Politician.objects.filter(we_vote_id__in=recommended_politician_we_vote_ids)

        politician_linked_campaignx_we_vote_id = ''
        if len(linked_campaignx_list) > 0:
            linked_campaignx = linked_campaignx_list[0]
            if linked_campaignx and positive_value_exists(linked_campaignx.we_vote_id):
                politician_linked_campaignx_we_vote_id = linked_campaignx.we_vote_id
        elif positive_value_exists(politician_on_stage.linked_campaignx_we_vote_id):
            politician_linked_campaignx_we_vote_id = politician_on_stage.linked_campaignx_we_vote_id

        queryset = PoliticianChangeLog.objects.using('readonly').all()
        queryset = queryset.filter(politician_we_vote_id__iexact=politician_we_vote_id)
        queryset = queryset.order_by('-log_datetime')
        change_log_list = list(queryset)

        if 'localhost' in WEB_APP_ROOT_URL:
            web_app_root_url = 'https://localhost:3000'
        else:
            web_app_root_url = 'https://quality.WeVote.US'
        template_values = {
            'ballotpedia_politician_name_dict':
            {
                'label':    'Name from Ballotpedia',
                'id':       'ballotpedia_politician_name_id',
                'name':     'ballotpedia_politician_name',
                'value':     ballotpedia_politician_name if ballotpedia_politician_name else politician_on_stage.ballotpedia_politician_name
            },
            'ballotpedia_politician_url':   ballotpedia_politician_url,
            'birth_date_dict':
            {
                'label':    'Birthdate (format Feb. 16, 1955)',
                'id':       'birth_date_id',
                'name':     'birth_date',
                'value':     birth_date if birth_date else politician_on_stage.birth_date
            },
            'change_log_list':              change_log_list,
            'duplicate_politician_list':    duplicate_politician_list,
            'facebook_url':                 facebook_url,
            'facebook_url2':                facebook_url2,
            'facebook_url3':                facebook_url3,
            'first_name_dict':
            {
                'label':    'First Name',
                'id':       'first_name_id',
                'name':     'first_name',
                'value':     first_name if first_name else politician_on_stage.first_name
            },
            'last_name_dict':
            {
                'label':    'Last Name',
                'id':       'last_name_id',
                'name':     'last_name',
                'value':     last_name if last_name else politician_on_stage.last_name
            },
            'middle_name_dict':
            {
                'label':    'Middle Name',
                'id':       'middle_name_id',
                'name':     'middle_name',
                'value':     middle_name if middle_name else politician_on_stage.middle_name
            },
            'google_civic_candidate_name_dict':
            {
                'label':    'Politician Alt Name (for Google Civic matching)',
                'id':       'google_civic_candidate_name_id',
                'name':     'google_civic_candidate_name',
                'value':     google_civic_candidate_name if google_civic_candidate_name else politician_on_stage.google_civic_candidate_name
            },
            'google_civic_candidate_name2_dict':
            {
                'label':    'Politician Alt Name 2',
                'id':       'google_civic_candidate_name2_id',
                'name':     'google_civic_candidate_name2',
                'value':     google_civic_candidate_name2 if google_civic_candidate_name2 else politician_on_stage.google_civic_candidate_name2
            },
            'google_civic_candidate_name3_dict':
            {
                'label':    'Politician Alt Name 3',
                'id':       'google_civic_candidate_name3_id',
                'name':     'google_civic_candidate_name3',
                'value':     google_civic_candidate_name3 if google_civic_candidate_name3 else politician_on_stage.google_civic_candidate_name3
            },
            'instagram_handle':             instagram_handle,
            'linked_campaignx_list':        linked_campaignx_list,
            'linked_candidate_list':        linked_candidate_list,
            'linked_representative_list':   linked_representative_list,
            'maplight_id_dict':
            {
                'label':    'MapLight Id',
                'id':       'maplight_id_id',
                'name':     'maplight_id',
                'value':     maplight_id if maplight_id else politician_on_stage.maplight_id
            },
            'messages_on_stage':            messages_on_stage,
            'path_count':                   path_count,
            'path_list':                    path_list,
            'politician':                   politician_on_stage,
            'politician_email':             politician_email,
            'politician_email2':            politician_email2,
            'politician_email3':            politician_email3,
            'politician_id':                politician_id,
            'politician_email_dict':
            {
                'label':    'Politician Email',
                'id':       'politician_email_id',
                'name':     'politician_email',
                'value':     politician_email if politician_email else politician_on_stage.politician_email
            },
            'politician_email2_dict':
            {
                'label':    'Email 2',
                'id':       'politician_email2_id',
                'name':     'politician_email2',
                'value':     politician_email2 if politician_email2 else politician_on_stage.politician_email2
            },
            'politician_email3_dict':
            {
                'label':    'Email 3',
                'id':       'politician_email3_id',
                'name':     'politician_email3',
                'value':     politician_email3 if politician_email3 else politician_on_stage.politician_email3
            },
            'politician_linked_campaignx_we_vote_id':   politician_linked_campaignx_we_vote_id,
            'politician_name':              politician_name,
            'politician_phone_number_dict':
            {
                'label':    'Politician Phone',
                'id':       'politician_phone_number_id',
                'name':     'politician_phone_number',
                'value':     politician_phone_number if politician_phone_number else politician_on_stage.politician_phone_number
            },
            'politician_phone_number2_dict':
            {
                'label':    'Phone 2',
                'id':       'politician_phone_number2_id',
                'name':     'politician_phone_number2',
                'value':     politician_phone_number2 if politician_phone_number2 else politician_on_stage.politician_phone_number2
            },
            'politician_phone_number3_dict':
            {
                'label':    'Phone 3',
                'id':       'politician_phone_number3_id',
                'name':     'politician_phone_number3',
                'value':     politician_phone_number3 if politician_phone_number3 else politician_on_stage.politician_phone_number3
            },
            'politician_position_list':     politician_position_list,
            'politician_twitter_handle':    politician_twitter_handle,
            'politician_twitter_handle2':   politician_twitter_handle2,
            'politician_twitter_handle3':   politician_twitter_handle3,
            'politician_twitter_handle4':   politician_twitter_handle4,
            'politician_twitter_handle5':   politician_twitter_handle5,
            'politician_contact_form_url':  politician_contact_form_url,
            'politician_url':               politician_url,
            'politician_url2':              politician_url2,
            'politician_url3':              politician_url3,
            'politician_url4':              politician_url4,
            'politician_url5':              politician_url5,
            'political_party':              political_party,
            'recommended_politicians_list': recommended_politicians_list,
            'political_party_dict':
            {
                'label':    'Politician Party',
                'id':       'political_party_id',
                'name':     'political_party',
                'value':     political_party if political_party else politician_on_stage.political_party
            },
            'rating_list':                  rating_list,
            'related_campaignx_list':       related_campaignx_list,
            'related_candidate_list':       related_candidate_list,
            'related_representative_list':  related_representative_list,
            'state_code':                   state_code,
            'state_code_dict':
            {
                'label':    'State Code',
                'id':       'state_code_id',
                'name':     'state_code',
                'value':     state_code if state_code else politician_on_stage.state_code
            },
            'vote_smart_id':                vote_smart_id,
            'vote_smart_id_dict':
            {
                'label':    'Vote Smart Id',
                'id':       'vote_smart_id_id',
                'name':     'vote_smart_id',
                'value':     vote_smart_id if vote_smart_id else politician_on_stage.vote_smart_id
            },
            'vote_usa_politician_id_dict':
            {
                'label':    'Vote USA Politician Id',
                'id':       'vote_usa_politician_id_id',
                'name':     'vote_usa_politician_id',
                'value':     vote_usa_politician_id if vote_usa_politician_id else politician_on_stage.vote_usa_politician_id
            },
            'web_app_root_url':             web_app_root_url,
            'youtube_url_dict':
            {
                'label':    'YouTube URL',
                'id':       'youtube_url_id',
                'name':     'youtube_url',
                'value':     youtube_url if youtube_url else politician_on_stage.youtube_url
            },
        }
        
        if positive_value_exists(politician_on_stage.we_vote_hosted_profile_image_url_large):
            if politician_on_stage.profile_image_background_color_needed is not False:
                politician_on_stage.profile_image_background_color = generate_background(politician_on_stage)
                politician_on_stage.profile_image_background_color_needed = False
                politician_on_stage.save()
                messages.add_message(request, messages.INFO, "Background color generated")       
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            # Incoming variables
            'vote_smart_id':        vote_smart_id,
        }
    return render(request, 'politician/politician_edit.html', template_values)


@login_required
def politicians_not_duplicates_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician1_we_vote_id = request.GET.get('politician1_we_vote_id', '')
    politician2_we_vote_id = request.GET.get('politician2_we_vote_id', '')
    state_code = request.GET.get('state_code', '')
    status = ""
    volunteer_task_manager = VolunteerTaskManager()
    voter_id = 0
    voter_we_vote_id = ""
    voter_device_id = get_voter_api_device_id(request)
    if positive_value_exists(voter_device_id):
        voter = fetch_voter_from_voter_device_link(voter_device_id)
        if hasattr(voter, 'we_vote_id'):
            voter_id = voter.id
            voter_we_vote_id = voter.we_vote_id

    politician_manager = PoliticianManager()
    results = politician_manager.update_or_create_politicians_are_not_duplicates(
        politician1_we_vote_id, politician2_we_vote_id)
    if results['success']:
        queryset = PoliticiansArePossibleDuplicates.objects.filter(
            politician1_we_vote_id__iexact=politician1_we_vote_id,
            politician2_we_vote_id__iexact=politician2_we_vote_id,
        )
        queryset.delete()
        messages.add_message(request, messages.INFO, 'Two politicians marked as not duplicates.')
        if positive_value_exists(voter_we_vote_id):
            try:
                # Give the volunteer who entered this credit
                task_results = volunteer_task_manager.create_volunteer_task_completed(
                    action_constant=VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION,
                    voter_id=voter_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
            except Exception as e:
                status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED-DEDUPLICATION: ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    else:
        messages.add_message(request, messages.ERROR,
                             'Could not save politicians_are_not_duplicates entry: ' +
                             results['status'])
    return HttpResponseRedirect(reverse('politician:duplicates_list', args=()) +
                                "?state_code=" + str(state_code))


def politician_change_gender_id_view(changes):
    count = 0
    for change in changes:
        try:
            politician_query = Politician.objects.filter(we_vote_id=change['we_vote_id'])
            politician_query = politician_query
            politician_list = list(politician_query)
            politician = politician_list[0]
            if change['gender'] == 'S':  # If set to "Save Unknown", then save as "Unknown"
                setattr(politician, 'gender', UNKNOWN)
                setattr(politician, 'gender_likelihood', POLITICAL_DATA_MANAGER)
            else:
                setattr(politician, 'gender', change['gender'])
                if 'gender_likelihood' in change:
                    try:
                        setattr(politician, 'gender_likelihood', change['gender_likelihood'])
                    except Exception as err:
                        logger.error('politician_change_gender_id gender_likelihood caught: ', err)
            # timezone = pytz.timezone("America/Los_Angeles")
            # datetime_now = timezone.localize(datetime.now())
            datetime_now = generate_localized_datetime_from_obj()[1]
            setattr(politician, 'date_last_changed', datetime_now)
            politician.save()
            count += 1
        except Exception as err:
            logger.error('politician_change_gender_id caught: ', err)
            count = -1

    return count


@login_required
def set_missing_gender_ids_view(request):
    """
    Process repair imported names form
    https://wevotedeveloper.com:8000/apis/v1/set_missing_gender_ids/?start=0&count=25
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    start = int(request.GET.get('start', 0))
    count = int(request.GET.get('count', 15))
    show_unknowns = request.GET.get('show_unknowns', True)
    politician_manager = PoliticianManager()
    list_of_people_from_db, number_of_rows = politician_manager.retrieve_politicians_with_no_gender_id(
        start, count, show_unknowns)
    people_list = []
    for person in list_of_people_from_db:
        if not hasattr(person, 'politician_name'):
            continue
        name = person.politician_name
        cleaned = re.sub("\(|\)|\"|\'", " ", name)
        cleaned = re.sub("\s+", "+", cleaned)
        search = 'https://www.google.com/search?q=' + cleaned
        politician_url = "/politician/{politician_id}/edit".format(politician_id=person.id)
        politician_state_code = person.state_code.upper() if person.state_code else ''
        politician_political_party = person.political_party.lower().capitalize() if person.political_party else ''

        person_item = {
            'person_name':                  name,
            'politician_url':               politician_url,
            'search_url':                   search,
            'gender':                       person.gender,
            'gender_guess':                 person.guess,
            'displayable_guess':            person.displayable_guess,
            'google_civic_candidate_name':  person.google_civic_candidate_name,
            'date_last_updated':            person.date_last_updated,
            'state_code':                   politician_state_code,
            'we_vote_id':                   person.we_vote_id,
            'we_vote_hosted_profile_image_url_medium':  person.we_vote_hosted_profile_image_url_medium,
            'party':                        politician_political_party,
        }
        people_list.append(person_item)

    template_values = {
        'number_of_rows':                   f'{number_of_rows:,}',
        'people_list':                      people_list,
        'index_offset':                     start,
        'show_unknowns':                    show_unknowns,
        'return_link':                      '/politician/',
    }
    return render(request, 'politician/politician_gender_id_fix_list.html', template_values)


def politician_change_names(changes):
    count = 0
    for change in changes:
        try:
            politician_query = Politician.objects.filter(we_vote_id=change['we_vote_id'])
            politician_query = politician_query
            politician_list = list(politician_query)
            politician = politician_list[0]
            setattr(politician, 'politician_name', change['name_after'])
            # timezone = pytz.timezone("America/Los_Angeles")
            # datetime_now = timezone.localize(datetime.now())
            datetime_now = generate_localized_datetime_from_obj()[1]
            setattr(politician, 'date_last_changed', datetime_now)
            politician.save()
            count += 1
        except Exception as err:
            logger.error('politician_change_names caught: ', err)
            count = -1

    return count


@login_required
def politician_edit_process_view(request):
    """
    Process the new or edit politician forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    change_description = ""
    change_description_changed = False
    changes_found_dict = {}
    primary_twitter_handle_changed = False
    status = ''
    success = True
    update_message = ''
    volunteer_task_manager = VolunteerTaskManager()

    ballot_guide_official_statement = request.POST.get('ballot_guide_official_statement', False)
    ballotpedia_politician_name = request.POST.get('ballotpedia_politician_name', False)
    ballotpedia_politician_url = request.POST.get('ballotpedia_politician_url', False)
    birth_date = request.POST.get('birth_date', False)
    first_name = request.POST.get('first_name', False)
    gender = request.POST.get('gender', 'False')
    middle_name = request.POST.get('middle_name', False)
    last_name = request.POST.get('last_name', False)
    profile_image_background_color = request.POST.get('profile_image_background_color', False)
    regenerate_color = request.POST.get('regenerate_color', False)
    facebook_url = request.POST.get('facebook_url', False)
    facebook_url2 = request.POST.get('facebook_url2', False)
    facebook_url3 = request.POST.get('facebook_url3', False)
    google_civic_candidate_name = request.POST.get('google_civic_candidate_name', False)
    google_civic_candidate_name2 = request.POST.get('google_civic_candidate_name2', False)
    google_civic_candidate_name3 = request.POST.get('google_civic_candidate_name3', False)
    instagram_handle = request.POST.get('instagram_handle', False)
    if positive_value_exists(instagram_handle):
        instagram_handle = extract_instagram_handle_from_text_string(instagram_handle)
    linkedin_url = request.POST.get('linkedin_url', False)
    maplight_id = request.POST.get('maplight_id', False)
    candidate_analysis_comment = request.POST.get('candidate_analysis_comment', '')
    if positive_value_exists(candidate_analysis_comment):
        change_description += "ANALYSIS_COMMENT: " + candidate_analysis_comment + " "
        change_description_changed = True
    politician_email = request.POST.get('politician_email', False)
    politician_email2 = request.POST.get('politician_email2', False)
    politician_email3 = request.POST.get('politician_email3', False)
    politician_id = request.POST.get('politician_id', 0)
    politician_id = convert_to_int(politician_id)
    politician_name = request.POST.get('politician_name', False)
    politician_phone_number = request.POST.get('politician_phone_number', False)
    politician_phone_number2 = request.POST.get('politician_phone_number2', False)
    politician_phone_number3 = request.POST.get('politician_phone_number3', False)
    try:
        politician_photo_file = request.FILES['politician_photo_file']
        politician_photo_file_found = True
    except Exception as e:
        politician_photo_file = None
        politician_photo_file_found = False
    politician_photo_file_delete = positive_value_exists(request.POST.get('politician_photo_file_delete', False))
    politician_twitter_handle = request.POST.get('politician_twitter_handle', False)
    if positive_value_exists(politician_twitter_handle):
        politician_twitter_handle = extract_twitter_handle_from_text_string(politician_twitter_handle)
    politician_twitter_handle2 = request.POST.get('politician_twitter_handle2', False)
    if positive_value_exists(politician_twitter_handle2) or politician_twitter_handle2 == '':
        politician_twitter_handle2 = extract_twitter_handle_from_text_string(politician_twitter_handle2)
    politician_twitter_handle3 = request.POST.get('politician_twitter_handle3', False)
    if positive_value_exists(politician_twitter_handle3) or politician_twitter_handle3 == '':
        politician_twitter_handle3 = extract_twitter_handle_from_text_string(politician_twitter_handle3)
    politician_twitter_handle4 = request.POST.get('politician_twitter_handle4', False)
    if positive_value_exists(politician_twitter_handle4) or politician_twitter_handle4 == '':
        politician_twitter_handle4 = extract_twitter_handle_from_text_string(politician_twitter_handle4)
    politician_twitter_handle5 = request.POST.get('politician_twitter_handle5', False)
    if positive_value_exists(politician_twitter_handle5) or politician_twitter_handle5 == '':
        politician_twitter_handle5 = extract_twitter_handle_from_text_string(politician_twitter_handle5)
    politician_contact_form_url = request.POST.get('politician_contact_form_url', False)
    politician_url = request.POST.get('politician_url', False)
    politician_url2 = request.POST.get('politician_url2', False)
    politician_url3 = request.POST.get('politician_url3', False)
    politician_url4 = request.POST.get('politician_url4', False)
    politician_url5 = request.POST.get('politician_url5', False)
    political_party = request.POST.get('political_party', False)
    profile_image_type_currently_active = request.POST.get('profile_image_type_currently_active', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)
    seo_friendly_path = request.POST.get('seo_friendly_path', False)
    state_code = request.POST.get('state_code', False)
    twitter_handle_updates_failing = request.POST.get('twitter_handle_updates_failing', False)
    twitter_handle_updates_failing = positive_value_exists(twitter_handle_updates_failing)
    twitter_handle2_updates_failing = request.POST.get('twitter_handle2_updates_failing', False)
    twitter_handle2_updates_failing = positive_value_exists(twitter_handle2_updates_failing)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    vote_usa_politician_id = request.POST.get('vote_usa_politician_id', False)
    wikipedia_url = request.POST.get('wikipedia_url', False)
    youtube_url = request.POST.get('youtube_url', False)
    # is_battleground_race_ values taken in below

    from campaign.controllers import update_campaignx_from_politician
    campaignx_manager = CampaignXManager()

    # Check to see if this politician already exists
    politician_on_stage_found = False
    politician_on_stage = Politician()
    politician_manager = PoliticianManager()
    if positive_value_exists(politician_id):
        try:
            politician_query = Politician.objects.filter(id=politician_id)
            if len(politician_query):
                politician_on_stage = politician_query[0]
                politician_we_vote_id = politician_on_stage.we_vote_id
                politician_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not retrieve politician: ' + str(e))
            success = False

    # Check to see if there is a duplicate politician already saved
    existing_politician_found = False
    if not positive_value_exists(politician_id):
        try:
            filter_list = Q()

            at_least_one_filter = False
            if positive_value_exists(vote_smart_id):
                at_least_one_filter = True
                filter_list |= Q(vote_smart_id=vote_smart_id)
            if positive_value_exists(maplight_id):
                at_least_one_filter = True
                filter_list |= Q(maplight_id=maplight_id)
            if positive_value_exists(politician_twitter_handle):
                at_least_one_filter = True
                filter_list |= (
                    Q(politician_twitter_handle=politician_twitter_handle) |
                    Q(politician_twitter_handle2=politician_twitter_handle) |
                    Q(politician_twitter_handle3=politician_twitter_handle) |
                    Q(politician_twitter_handle4=politician_twitter_handle) |
                    Q(politician_twitter_handle5=politician_twitter_handle)
                )
            if positive_value_exists(politician_twitter_handle2):
                at_least_one_filter = True
                filter_list |= (
                    Q(politician_twitter_handle=politician_twitter_handle2) |
                    Q(politician_twitter_handle2=politician_twitter_handle2) |
                    Q(politician_twitter_handle3=politician_twitter_handle2) |
                    Q(politician_twitter_handle4=politician_twitter_handle2) |
                    Q(politician_twitter_handle5=politician_twitter_handle2)
                )
            if positive_value_exists(politician_twitter_handle3):
                at_least_one_filter = True
                filter_list |= (
                    Q(politician_twitter_handle=politician_twitter_handle3) |
                    Q(politician_twitter_handle2=politician_twitter_handle3) |
                    Q(politician_twitter_handle3=politician_twitter_handle3) |
                    Q(politician_twitter_handle4=politician_twitter_handle3) |
                    Q(politician_twitter_handle5=politician_twitter_handle3)
                )
            if positive_value_exists(politician_twitter_handle4):
                at_least_one_filter = True
                filter_list |= (
                    Q(politician_twitter_handle=politician_twitter_handle4) |
                    Q(politician_twitter_handle2=politician_twitter_handle4) |
                    Q(politician_twitter_handle3=politician_twitter_handle4) |
                    Q(politician_twitter_handle4=politician_twitter_handle4) |
                    Q(politician_twitter_handle5=politician_twitter_handle4)
                )
            if positive_value_exists(politician_twitter_handle5):
                at_least_one_filter = True
                filter_list |= (
                    Q(politician_twitter_handle=politician_twitter_handle5) |
                    Q(politician_twitter_handle2=politician_twitter_handle5) |
                    Q(politician_twitter_handle3=politician_twitter_handle5) |
                    Q(politician_twitter_handle4=politician_twitter_handle5) |
                    Q(politician_twitter_handle5=politician_twitter_handle5)
                )

            if at_least_one_filter:
                politician_duplicates_query = Politician.objects.filter(filter_list)

                if len(politician_duplicates_query):
                    existing_politician_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not retrieve politician: ' + str(e))
            success = False

    # We can use the same url_variables with any processing failures below
    url_variables = "?ballot_guide_official_statement=" + str(ballot_guide_official_statement) + \
                    "&ballotpedia_politician_name=" + str(ballotpedia_politician_name) + \
                    "&ballotpedia_politician_url=" + str(ballotpedia_politician_url) + \
                    "&state_code=" + str(state_code) + \
                    "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                    "&google_civic_candidate_name2=" + str(google_civic_candidate_name2) + \
                    "&google_civic_candidate_name3=" + str(google_civic_candidate_name3) + \
                    "&instagram_handle=" + str(instagram_handle) + \
                    "&politician_contact_form_url=" + str(politician_contact_form_url) + \
                    "&politician_name=" + str(politician_name) + \
                    "&politician_email=" + str(politician_email) + \
                    "&politician_email2=" + str(politician_email2) + \
                    "&politician_email3=" + str(politician_email3) + \
                    "&politician_phone_number=" + str(politician_phone_number) + \
                    "&politician_phone_number2=" + str(politician_phone_number2) + \
                    "&politician_phone_number3=" + str(politician_phone_number3) + \
                    "&politician_twitter_handle=" + str(politician_twitter_handle) + \
                    "&politician_twitter_handle2=" + str(politician_twitter_handle2) + \
                    "&politician_twitter_handle3=" + str(politician_twitter_handle3) + \
                    "&politician_twitter_handle4=" + str(politician_twitter_handle4) + \
                    "&politician_twitter_handle5=" + str(politician_twitter_handle5) + \
                    "&politician_url=" + str(politician_url) + \
                    "&politician_url2=" + str(politician_url2) + \
                    "&politician_url3=" + str(politician_url3) + \
                    "&politician_url4=" + str(politician_url4) + \
                    "&politician_url5=" + str(politician_url5) + \
                    "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                    "&political_party=" + str(political_party) + \
                    "&vote_smart_id=" + str(vote_smart_id) + \
                    "&maplight_id=" + str(maplight_id) + \
                    "&first_name=" + str(first_name) + \
                    "&middle_name=" + str(middle_name) + \
                    "&last_name=" + str(last_name) + \
                    "&ballotpedia_politician_name=" + str(ballotpedia_politician_name) + \
                    "&vote_smart_id=" + str(vote_smart_id) + \
                    "&birth_date=" + str(birth_date) + \
                    "&youtube_url=" + str(youtube_url)

    if not success:
        messages.add_message(request, messages.ERROR,
                             'POLITICIAN_ERROR Please click the back arrow and report URL to the engineering team ')
        return HttpResponseRedirect(reverse('politician:politician_list', args=()) + url_variables)

    push_seo_friendly_path_changes = False
    try:
        if existing_politician_found:
            messages.add_message(request, messages.ERROR, 'This politician already exists.')
            return HttpResponseRedirect(reverse('politician:politician_new', args=()) + url_variables)
        elif politician_on_stage_found:
            # Update below
            pass
        else:
            # Create new
            required_politician_variables = True \
                if positive_value_exists(politician_name) \
                else False
            if required_politician_variables:
                politician_on_stage = Politician(
                    first_name=extract_first_name_from_full_name(politician_name),
                    middle_name=extract_middle_name_from_full_name(politician_name),
                    last_name=extract_last_name_from_full_name(politician_name),
                    politician_name=politician_name,
                    state_code=state_code,
                )
                politician_on_stage_found = True
        if politician_on_stage_found:
            # #################################################
            # Process incoming uploaded photo if there is one
            politician_photo_in_binary_format = None
            politician_photo_converted_to_binary = False
            if politician_photo_file_found:
                try:
                    politician_photo_in_binary_format = b64encode(politician_photo_file.read()).decode('utf-8')
                    politician_photo_converted_to_binary = True
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         "Error converting politician photo to binary: {error}".format(error=e))
            if politician_photo_file_found and politician_photo_converted_to_binary:
                changes_found_dict['is_photo_added'] = True
                change_description += "Photo ADDED "
                change_description_changed = True
                photo_results = politician_save_photo_from_file_reader(
                    politician_we_vote_id=politician_we_vote_id,
                    politician_photo_binary_file=politician_photo_in_binary_format)
                if photo_results['we_vote_hosted_politician_photo_original_url']:
                    we_vote_hosted_politician_photo_original_url = \
                        photo_results['we_vote_hosted_politician_photo_original_url']
                    # Now we want to resize to a large version
                    create_resized_image_results = create_resized_images(
                        politician_we_vote_id=politician_we_vote_id,
                        politician_uploaded_profile_image_url_https=we_vote_hosted_politician_photo_original_url)
                    politician_on_stage.we_vote_hosted_profile_uploaded_image_url_large = \
                        create_resized_image_results['cached_resized_image_url_large']
                    politician_on_stage.we_vote_hosted_profile_uploaded_image_url_medium = \
                        create_resized_image_results['cached_resized_image_url_medium']
                    politician_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny = \
                        create_resized_image_results['cached_resized_image_url_tiny']
                    if profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN \
                            or profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UPLOADED:
                        politician_on_stage.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UPLOADED
                        politician_on_stage.we_vote_hosted_profile_image_url_large = \
                            politician_on_stage.we_vote_hosted_profile_uploaded_image_url_large
                        politician_on_stage.we_vote_hosted_profile_image_url_medium = \
                            politician_on_stage.we_vote_hosted_profile_uploaded_image_url_medium
                        politician_on_stage.we_vote_hosted_profile_image_url_tiny = \
                            politician_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny
                        politician_on_stage.profile_image_background_color_needed = True
                    elif profile_image_type_currently_active is not False:
                        politician_on_stage.profile_image_type_currently_active = profile_image_type_currently_active
            elif politician_photo_file_delete:
                changes_found_dict['is_photo_removed'] = True
                change_description += "Photo REMOVED "
                change_description_changed = True

                politician_on_stage.we_vote_hosted_profile_uploaded_image_url_large = None
                politician_on_stage.we_vote_hosted_profile_uploaded_image_url_medium = None
                politician_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny = None
                if profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UPLOADED \
                        or profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                    profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UNKNOWN
                    politician_on_stage.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UNKNOWN
                    politician_on_stage.we_vote_hosted_profile_image_url_large = None
                    politician_on_stage.we_vote_hosted_profile_image_url_medium = None
                    politician_on_stage.we_vote_hosted_profile_image_url_tiny = None
            if profile_image_type_currently_active is not False:
                results = organize_object_photo_fields_based_on_image_type_currently_active(
                    object_with_photo_fields=politician_on_stage,
                    profile_image_type_currently_active=profile_image_type_currently_active,
                )
                if results['success']:
                    politician_on_stage = results['object_with_photo_fields']

            # ###############################################
            # Now process all other politician fields
            if ballot_guide_official_statement is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.ballot_guide_official_statement,
                    new_value=ballot_guide_official_statement,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_official_statement',
                    changes_found_key_name='Official Statement',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.ballot_guide_official_statement = ballot_guide_official_statement
            if ballotpedia_politician_name is not False:
                politician_on_stage.ballotpedia_politician_name = ballotpedia_politician_name
            ballotpedia_politician_url_changed = False
            if ballotpedia_politician_url is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.ballotpedia_politician_url,
                    new_value=ballotpedia_politician_url,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_ballotpedia',
                    changes_found_key_name='Ballotpedia',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                    ballotpedia_politician_url_changed = True
                politician_on_stage.ballotpedia_politician_url = ballotpedia_politician_url
                if not positive_value_exists(ballotpedia_politician_url):
                    politician_on_stage.ballotpedia_photo_url = None
                    politician_on_stage.ballotpedia_photo_url_is_broken = False
                    politician_on_stage.ballotpedia_photo_url_is_placeholder = False
                    politician_on_stage.we_vote_hosted_profile_ballotpedia_image_url_large = None
                    politician_on_stage.we_vote_hosted_profile_ballotpedia_image_url_medium = None
                    politician_on_stage.we_vote_hosted_profile_ballotpedia_image_url_tiny = None
                    if profile_image_type_currently_active == PROFILE_IMAGE_TYPE_BALLOTPEDIA:
                        politician_on_stage.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UNKNOWN
                        politician_on_stage.we_vote_hosted_profile_image_url_large = None
                        politician_on_stage.we_vote_hosted_profile_image_url_medium = None
                        politician_on_stage.we_vote_hosted_profile_image_url_tiny = None
                        results = organize_object_photo_fields_based_on_image_type_currently_active(
                            object_with_photo_fields=politician_on_stage)
                        if results['success']:
                            politician_on_stage = results['object_with_photo_fields']
            try:
                if birth_date is not False:
                    if birth_date == '':
                        politician_on_stage.birth_date = None
                    else:
                        politician_on_stage.birth_date = datetime.strptime(birth_date, '%b. %d, %Y')
            except Exception as e:
                messages.add_message(request, messages.ERROR, 'Could not save birthdate:' + str(e))
            if facebook_url is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.facebook_url,
                    new_value=facebook_url,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_facebook',
                    changes_found_key_name='Facebook',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.facebook_url = facebook_url
            if facebook_url2 is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.facebook_url2,
                    new_value=facebook_url2,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_facebook',
                    changes_found_key_name='Facebook2',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.facebook_url2 = facebook_url2
            if facebook_url3 is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.facebook_url3,
                    new_value=facebook_url3,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_facebook',
                    changes_found_key_name='Facebook3',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.facebook_url3 = facebook_url3
            if first_name is not False:
                politician_on_stage.first_name = first_name
            if middle_name is not False:
                politician_on_stage.middle_name = middle_name
            if last_name is not False:
                politician_on_stage.last_name = last_name
            if regenerate_color is not False:
                politician_on_stage.profile_image_background_color = generate_background(politician_on_stage)
                politician_on_stage.profile_image_background_color_needed = False
            elif profile_image_background_color is not False:
                if profile_image_background_color == '':
                    politician_on_stage.profile_image_background_color = None
                    politician_on_stage.profile_image_background_color_needed = False
                elif validate_hex(profile_image_background_color):
                    politician_on_stage.profile_image_background_color = profile_image_background_color
                    politician_on_stage.profile_image_background_color_needed = False
                else:
                    messages.add_message(request, messages.ERROR, 'Enter hex as \'#\' followed by six hexadecimal characters 0-9a-f')
            if gender is not False:
                gender = gender[0]
                if politician_on_stage.gender != gender:
                    politician_on_stage.gender_likelihood = POLITICAL_DATA_MANAGER
                if gender == 'U':
                    politician_on_stage.gender_likelihood = ''
                politician_on_stage.gender = gender
            if google_civic_candidate_name is not False:
                politician_on_stage.google_civic_candidate_name = google_civic_candidate_name
            if google_civic_candidate_name2 is not False:
                politician_on_stage.google_civic_candidate_name2 = google_civic_candidate_name2
            if google_civic_candidate_name3 is not False:
                politician_on_stage.google_civic_candidate_name3 = google_civic_candidate_name3
            if instagram_handle is not False:
                politician_on_stage.instagram_handle = instagram_handle  # handle extracted above (if URL)
            is_battleground_years_list = IS_BATTLEGROUND_YEARS_AVAILABLE
            years_false_list = []
            years_true_list = []
            for year in is_battleground_years_list:
                is_battleground_race_key = 'is_battleground_race_' + str(year)
                incoming_is_battleground_race = positive_value_exists(request.POST.get(is_battleground_race_key, False))
                if hasattr(politician_on_stage, is_battleground_race_key):
                    if incoming_is_battleground_race:
                        years_true_list.append(year)
                    else:
                        years_false_list.append(year)
                    setattr(politician_on_stage, is_battleground_race_key, incoming_is_battleground_race)
            years_list = list(set(years_false_list + years_true_list))
            if linkedin_url is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.linkedin_url,
                    new_value=linkedin_url,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_linkedin',
                    changes_found_key_name='LinkedIn',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.linkedin_url = linkedin_url
            if maplight_id is not False:
                politician_on_stage.maplight_id = maplight_id
            if politician_contact_form_url is not False:
                politician_on_stage.politician_contact_form_url = politician_contact_form_url
            if politician_email is not False:
                politician_on_stage.politician_email = politician_email
            if politician_email2 is not False:
                politician_on_stage.politician_email2 = politician_email2
            if politician_email3 is not False:
                politician_on_stage.politician_email3 = politician_email3
            if positive_value_exists(politician_on_stage.linked_campaignx_we_vote_id):
                campaignx_results = campaignx_manager.retrieve_campaignx(
                    campaignx_we_vote_id=politician_on_stage.linked_campaignx_we_vote_id)
                if campaignx_results['campaignx_found']:
                    # Continue below
                    pass
                elif campaignx_results['success']:
                    # If the linked_campaignx_we_vote_id points to a campaignx that doesn't exist anymore, unlink
                    politician_on_stage.linked_campaignx_we_vote_id = None
            if politician_name is not False:
                politician_on_stage.politician_name = politician_name
            if politician_phone_number is not False:
                politician_on_stage.politician_phone_number = politician_phone_number
            if politician_phone_number2 is not False:
                politician_on_stage.politician_phone_number2 = politician_phone_number2
            if politician_phone_number3 is not False:
                politician_on_stage.politician_phone_number3 = politician_phone_number3
            # Save current twitter_handle settings so we can compare values below
            current_politician_twitter_handle = politician_on_stage.politician_twitter_handle
            current_politician_twitter_handle2 = politician_on_stage.politician_twitter_handle2
            current_politician_twitter_handle3 = politician_on_stage.politician_twitter_handle3
            current_politician_twitter_handle4 = politician_on_stage.politician_twitter_handle4
            current_politician_twitter_handle5 = politician_on_stage.politician_twitter_handle5
            # Reset all politician_twitter_handles
            politician_on_stage.politician_twitter_handle = None
            politician_on_stage.politician_twitter_handle2 = None
            politician_on_stage.politician_twitter_handle3 = None
            politician_on_stage.politician_twitter_handle4 = None
            politician_on_stage.politician_twitter_handle5 = None
            if politician_twitter_handle is not False:
                change_results = change_tracking(
                    existing_value=current_politician_twitter_handle,
                    new_value=politician_twitter_handle,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_twitter_handle',
                    changes_found_key_name='TwitterHandle',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                    primary_twitter_handle_changed = True
                add_results = add_twitter_handle_to_next_politician_spot(
                    politician_on_stage, politician_twitter_handle)
                if add_results['success']:
                    politician_on_stage = add_results['politician']
            if politician_twitter_handle2 is not False:
                change_results = change_tracking(
                    existing_value=current_politician_twitter_handle2,
                    new_value=politician_twitter_handle2,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_twitter_handle',
                    changes_found_key_name='TwitterHandle2',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                add_results = add_twitter_handle_to_next_politician_spot(
                    politician_on_stage, politician_twitter_handle2)
                if add_results['success']:
                    politician_on_stage = add_results['politician']
            if politician_twitter_handle3 is not False:
                change_results = change_tracking(
                    existing_value=current_politician_twitter_handle3,
                    new_value=politician_twitter_handle3,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_twitter_handle',
                    changes_found_key_name='TwitterHandle3',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                add_results = add_twitter_handle_to_next_politician_spot(
                    politician_on_stage, politician_twitter_handle3)
                if add_results['success']:
                    politician_on_stage = add_results['politician']
            if politician_twitter_handle4 is not False:
                change_results = change_tracking(
                    existing_value=current_politician_twitter_handle4,
                    new_value=politician_twitter_handle4,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_twitter_handle',
                    changes_found_key_name='TwitterHandle4',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                add_results = add_twitter_handle_to_next_politician_spot(
                    politician_on_stage, politician_twitter_handle4)
                if add_results['success']:
                    politician_on_stage = add_results['politician']
            if politician_twitter_handle5 is not False:
                change_results = change_tracking(
                    existing_value=current_politician_twitter_handle5,
                    new_value=politician_twitter_handle5,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_twitter_handle',
                    changes_found_key_name='TwitterHandle5',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                add_results = add_twitter_handle_to_next_politician_spot(
                    politician_on_stage, politician_twitter_handle5)
                if add_results['success']:
                    politician_on_stage = add_results['politician']
            if politician_url is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.politician_url,
                    new_value=politician_url,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_politician_url',
                    changes_found_key_name='URL',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.politician_url = politician_url
            if politician_url2 is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.politician_url2,
                    new_value=politician_url2,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_politician_url',
                    changes_found_key_name='URL2',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.politician_url2 = politician_url2
            if politician_url3 is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.politician_url3,
                    new_value=politician_url3,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_politician_url',
                    changes_found_key_name='URL3',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.politician_url3 = politician_url3
            if politician_url4 is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.politician_url4,
                    new_value=politician_url4,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_politician_url',
                    changes_found_key_name='URL4',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.politician_url4 = politician_url4
            if politician_url5 is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.politician_url5,
                    new_value=politician_url5,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_politician_url',
                    changes_found_key_name='URL5',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.politician_url5 = politician_url5
            if political_party is not False:
                political_party = convert_to_political_party_constant(political_party)
                politician_on_stage.political_party = political_party
            if state_code is not False:
                politician_on_stage.state_code = state_code
            if seo_friendly_path is not False:
                # If path isn't passed in, create one. If provided, verify it is unique.
                seo_results = politician_manager.generate_seo_friendly_path(
                    base_pathname_string=seo_friendly_path,
                    politician_name=politician_on_stage.politician_name,
                    politician_we_vote_id=politician_on_stage.we_vote_id,
                    state_code=politician_on_stage.state_code)
                if seo_results['success']:
                    seo_friendly_path = seo_results['seo_friendly_path']
                if not positive_value_exists(seo_friendly_path):
                    seo_friendly_path = None
                if seo_friendly_path != politician_on_stage.seo_friendly_path:
                    # Update linked candidate & representative entries to use this latest seo_friendly_path
                    push_seo_friendly_path_changes = True
                politician_on_stage.seo_friendly_path = seo_friendly_path

            # if politician_on_stage.twitter_handle_updates_failing != twitter_handle_updates_failing:
            #     changes_found_dict['is_twitter_handle_removed'] = True
            # twitter_handle_updates_failing
            change_results = change_tracking_boolean(
                existing_value=politician_on_stage.twitter_handle_updates_failing,
                new_value=twitter_handle_updates_failing,
                changes_found_dict=changes_found_dict,
                changes_found_key_base='is_twitter_handle',
                changes_found_key_name='Twitter Updates Failing',
            )
            changes_found_dict = change_results['changes_found_dict']
            if change_results['change_description_changed']:
                change_description += change_results['change_description']
                change_description_changed = True
            politician_on_stage.twitter_handle_updates_failing = twitter_handle_updates_failing

            # if politician_on_stage.twitter_handle2_updates_failing != twitter_handle2_updates_failing:
            #     changes_found_dict['is_twitter_handle_removed'] = True
            # twitter_handle2_updates_failing
            change_results = change_tracking_boolean(
                existing_value=politician_on_stage.twitter_handle2_updates_failing,
                new_value=twitter_handle2_updates_failing,
                changes_found_dict=changes_found_dict,
                changes_found_key_base='is_twitter_handle',
                changes_found_key_name='Twitter2 Updates Failing',
            )
            changes_found_dict = change_results['changes_found_dict']
            if change_results['change_description_changed']:
                change_description += change_results['change_description']
                change_description_changed = True
            politician_on_stage.twitter_handle2_updates_failing = twitter_handle2_updates_failing

            if vote_smart_id is not False:
                politician_on_stage.vote_smart_id = vote_smart_id
            if politician_we_vote_id is not False:
                politician_on_stage.we_vote_id = politician_we_vote_id
            if vote_usa_politician_id is not False:
                politician_on_stage.vote_usa_politician_id = vote_usa_politician_id
            if wikipedia_url is not False:
                change_results = change_tracking(
                    existing_value=politician_on_stage.wikipedia_url,
                    new_value=wikipedia_url,
                    changes_found_dict=changes_found_dict,
                    changes_found_key_base='is_wikipedia',
                    changes_found_key_name='Wikipedia',
                )
                changes_found_dict = change_results['changes_found_dict']
                if change_results['change_description_changed']:
                    change_description += change_results['change_description']
                    change_description_changed = True
                politician_on_stage.wikipedia_url = wikipedia_url
                politician_on_stage.wikipedia_photo_does_not_exist = False

                # politician_on_stage.wikipedia_photo_url_is_broken = wikipedia_photo_url_is_broken
            if youtube_url is not False:
                politician_on_stage.youtube_url = youtube_url

            politician_on_stage.save()
            politician_we_vote_id = politician_on_stage.we_vote_id
            vote_usa_politician_id = politician_on_stage.vote_usa_politician_id
            politician_id = politician_on_stage.id

            if (ballotpedia_politician_url_changed \
                or not positive_value_exists(politician_on_stage.ballotpedia_photo_url)) \
                    and positive_value_exists(ballotpedia_politician_url):
                results = get_photo_url_from_ballotpedia(
                    incoming_object=politician_on_stage,
                    save_to_database=True,
                )

            # Now generate_seo_friendly_path if there isn't one
            seo_results = politician_manager.generate_seo_friendly_path(
                base_pathname_string=politician_on_stage.seo_friendly_path,
                politician_name=politician_on_stage.politician_name,
                politician_we_vote_id=politician_on_stage.we_vote_id,
                state_code=politician_on_stage.state_code)
            if seo_results['success']:
                seo_friendly_path = seo_results['seo_friendly_path']
                if positive_value_exists(seo_friendly_path):
                    politician_on_stage.seo_friendly_path = seo_friendly_path
                    politician_on_stage.save()
            messages.add_message(request, messages.INFO, 'Politician saved.')

            if positive_value_exists(politician_on_stage.linked_campaignx_we_vote_id):
                campaignx_results = campaignx_manager.retrieve_campaignx(
                    campaignx_we_vote_id=politician_on_stage.linked_campaignx_we_vote_id)
                if campaignx_results['campaignx_found']:
                    campaignx = campaignx_results['campaignx']
                    results = update_campaignx_from_politician(campaignx=campaignx, politician=politician_on_stage)
                    if results['success']:
                        campaignx = results['campaignx']
                        campaignx.date_last_updated_from_politician = localtime(now()).date()
                        campaignx.save()

            # Find current representative for this politician
            representative_manager = RepresentativeManager()
            rep_results = representative_manager.retrieve_representative(
                politician_we_vote_id=politician_on_stage.we_vote_id)
            if rep_results['representative_found']:
                from representative.controllers import update_representative_details_from_politician
                representative = rep_results['representative']
                results = update_representative_details_from_politician(
                    representative=representative,
                    politician=politician_on_stage)
                if results['success']:
                    if results['save_changes']:
                        representative = results['representative']
                        representative.date_last_updated_from_politician = localtime(now()).date()
                        representative.save()
        else:
            # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
            if positive_value_exists(politician_id):
                return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)) +
                                            url_variables)
            else:
                return HttpResponseRedirect(reverse('politician:politician_new', args=()) +
                                            url_variables)

    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, "Could not save politician. Error:" + str(e))
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))

    if positive_value_exists(politician_we_vote_id) and len(years_list) > 0:
        from politician.controllers import update_parallel_fields_with_years_in_related_objects
        results = update_parallel_fields_with_years_in_related_objects(
            field_key_root='is_battleground_race_',
            master_we_vote_id_updated=politician_we_vote_id,
            years_false_list=years_false_list,
            years_true_list=years_true_list,
        )
        if not results['success']:
            status += results['status']
            status += "FAILED_TO_UPDATE_PARALLEL_FIELDS_FROM_POLITICIAN "
            messages.add_message(request, messages.ERROR, status)

    position_list_manager = PositionListManager()
    # ##################################
    # Unlink Candidates from this Politician if "unlink_candidate_XXXXX_from_politician" passed in
    try:
        linked_candidate_query = CandidateCampaign.objects.all()
        linked_candidate_query = linked_candidate_query.filter(
            Q(politician_we_vote_id__iexact=politician_on_stage.we_vote_id) |
            Q(politician_id=politician_on_stage.id)
        )
        linked_candidate_list = list(linked_candidate_query)
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'LINKED_CANDIDATE_PROBLEM: ' + str(e))
        linked_candidate_list = []
    for candidate in linked_candidate_list:
        if positive_value_exists(candidate.id):
            variable_name = "unlink_candidate_" + str(candidate.id) + "_from_politician"
            unlink_candidate = positive_value_exists(request.POST.get(variable_name, False))
            if positive_value_exists(unlink_candidate) and positive_value_exists(politician_we_vote_id):
                candidate.politician_we_vote_id = None
                candidate.politician_id = None
                candidate.seo_friendly_path = None
                candidate.save()
                # Now update positions
                results = position_list_manager.update_politician_we_vote_id_in_all_positions(
                    candidate_we_vote_id=candidate.we_vote_id,
                    new_politician_id=None,
                    new_politician_we_vote_id=None)

                messages.add_message(request, messages.INFO,
                                     'Candidate unlinked, number of positions changed: {number_changed}'
                                     ''.format(number_changed=results['number_changed']))
            else:
                pass

    # ##################################
    # Unlink Representatives from this Politician if "unlink_representative_XXXXX_from_politician" passed in
    try:
        linked_representative_query = Representative.objects.all()
        linked_representative_query = linked_representative_query.filter(
            Q(politician_we_vote_id__iexact=politician_on_stage.we_vote_id) |
            Q(politician_id=politician_on_stage.id)
        )
        linked_representative_list = list(linked_representative_query)
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'LINKED_REPRESENTATIVE_PROBLEM: ' + str(e))
        linked_representative_list = []
    for representative in linked_representative_list:
        if positive_value_exists(representative.id):
            variable_name = "unlink_representative_" + str(representative.id) + "_from_politician"
            unlink_representative = positive_value_exists(request.POST.get(variable_name, False))
            if positive_value_exists(unlink_representative) and positive_value_exists(politician_we_vote_id):
                representative.politician_we_vote_id = None
                representative.politician_id = None
                representative.seo_friendly_path = None
                representative.save()

                messages.add_message(request, messages.INFO, 'Representative unlinked.')
            else:
                pass

    # ##################################
    # Find Candidates to Link to this Politician
    # Finding Candidates that *might* be "children" of this politician
    from politician.controllers import find_candidates_to_link_to_this_politician

    related_candidate_list = find_candidates_to_link_to_this_politician(politician=politician_on_stage)

    # ##################################
    # Link Candidates to this Politician
    for candidate in related_candidate_list:
        if positive_value_exists(candidate.id):
            variable_name = "link_candidate_" + str(candidate.id) + "_to_politician"
            link_candidate = positive_value_exists(request.POST.get(variable_name, False))
            if positive_value_exists(link_candidate) and positive_value_exists(politician_we_vote_id):
                candidate.politician_id = politician_id
                candidate.politician_we_vote_id = politician_we_vote_id
                candidate.seo_friendly_path = politician_on_stage.seo_friendly_path
                if not positive_value_exists(candidate.vote_usa_politician_id) and \
                        positive_value_exists(vote_usa_politician_id):
                    candidate.vote_usa_politician_id = vote_usa_politician_id
                candidate.save()
                # Now update positions
                results = position_list_manager.update_politician_we_vote_id_in_all_positions(
                    candidate_we_vote_id=candidate.we_vote_id,
                    new_politician_id=politician_id,
                    new_politician_we_vote_id=politician_we_vote_id)

                messages.add_message(request, messages.INFO,
                                     'Candidate linked, number of positions changed: {number_changed}'
                                     ''.format(number_changed=results['number_changed']))
            else:
                pass

    # ##################################
    # Find Representatives to Link to this Politician
    # Finding Representatives that *might* be "children" of this politician
    from politician.controllers import find_representatives_to_link_to_this_politician
    related_representative_list = find_representatives_to_link_to_this_politician(politician=politician_on_stage)

    # ##################################
    # Link Representatives to this Politician
    for representative in related_representative_list:
        if positive_value_exists(representative.id):
            variable_name = "link_representative_" + str(representative.id) + "_to_politician"
            link_representative = positive_value_exists(request.POST.get(variable_name, False))
            if positive_value_exists(link_representative) and positive_value_exists(politician_we_vote_id):
                representative.politician_id = politician_id
                representative.politician_we_vote_id = politician_we_vote_id
                representative.seo_friendly_path = politician_on_stage.seo_friendly_path
                if not positive_value_exists(representative.vote_usa_politician_id) and \
                        positive_value_exists(vote_usa_politician_id):
                    representative.vote_usa_politician_id = vote_usa_politician_id
                representative.save()

    # Update Linked CampaignXs with seo_friendly_path
    if success and positive_value_exists(politician_on_stage.we_vote_id) and \
            positive_value_exists(politician_on_stage.linked_campaignx_we_vote_id):
        heal_linked_campaignx_variables = True
        campaignx_manager = CampaignXManager()
        campaignx_results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=politician_on_stage.linked_campaignx_we_vote_id,
        )
        if not campaignx_results['success']:
            status += campaignx_results['status']
            status += "FAILED_TO_RETRIEVE_CAMPAIGNX_LINKED_TO_POLITICIAN "
            messages.add_message(request, messages.ERROR, status)
        elif campaignx_results['campaignx_found']:
            campaignx = campaignx_results['campaignx']
            if positive_value_exists(campaignx.linked_politician_we_vote_id) \
                    and campaignx.linked_politician_we_vote_id != politician_on_stage.we_vote_id:
                heal_linked_campaignx_variables = False
            if heal_linked_campaignx_variables and not positive_value_exists(campaignx.linked_politician_we_vote_id):
                campaignx.linked_politician_we_vote_id = politician_on_stage.we_vote_id
                try:
                    campaignx.save()
                    messages.add_message(request, messages.INFO, "Campaignx updated with linked_politician_we_vote_id.")
                except Exception as e:
                    messages.add_message(request, messages.ERROR, "Cannot heal Campaignx linked_politician_we_vote_id:"
                                                                  "" + str(e))
                    heal_linked_campaignx_variables = False
            if heal_linked_campaignx_variables and positive_value_exists(politician_on_stage.seo_friendly_path) \
                    and campaignx.seo_friendly_path != politician_on_stage.seo_friendly_path:
                # Consider saving politician_on_stage.seo_friendly_path into CampaignXSEOFriendlyPath,
                #  so we can maintain connection to this campaignx if the politician_on_stage.seo_friendly_path changes
                # The problem with doing that, is that when we relegate this campaignx to the past, we will have
                #  a politician-generated seo_friendly_path linked to a former campaignx, causing a collision.
                # When we unlink campaigns by removing linked_politician_we_vote_id from CampaignX, we will want to
                #  generate a new seo_friendly_path for that historical campaignx.
                campaignx.seo_friendly_path = politician_on_stage.seo_friendly_path
                try:
                    campaignx.save()
                    messages.add_message(request, messages.INFO, "Campaignx updated with seo_friendly_path.")
                except Exception as e:
                    messages.add_message(request, messages.ERROR, "Cannot heal Campaignx seo_friendly_path:" + str(e))
                    heal_linked_campaignx_variables = False
            if not heal_linked_campaignx_variables:
                messages.add_message(request, messages.ERROR, "Cannot heal Campaignx linked variables.")

    # Update Linked Candidates with seo_friendly_path, and
    if success and positive_value_exists(politician_we_vote_id):
        candidate_list_manager = CandidateListManager()
        politician_we_vote_id_list = [politician_we_vote_id]
        candidate_results = candidate_list_manager.retrieve_candidate_list(
            politician_we_vote_id_list=politician_we_vote_id_list,
        )
        if not candidate_results['success']:
            status += candidate_results['status']
            status += "FAILED_TO_RETRIEVE_CANDIDATES_LINKED_TO_POLITICIAN "
            messages.add_message(request, messages.ERROR, status)
        update_list = []
        updates_needed = False
        updates_made = 0
        candidates_to_update_from_politician = []
        if candidate_results['candidate_list_found']:
            now_as_we_vote_date_string = convert_date_to_we_vote_date_string(now())
            now_as_integer = convert_we_vote_date_string_to_date_as_integer(now_as_we_vote_date_string)
            candidate_list = candidate_results['candidate_list']
            for candidate in candidate_list:
                if positive_value_exists(candidate.candidate_ultimate_election_date) \
                        and candidate.candidate_ultimate_election_date > now_as_integer:
                    candidates_to_update_from_politician.append(candidate)
                elif positive_value_exists(politician_on_stage.seo_friendly_path) and push_seo_friendly_path_changes:
                    candidate.seo_friendly_path = politician_on_stage.seo_friendly_path
                    update_list.append(candidate)
                    updates_needed = True
                    updates_made += 1
        if updates_needed:
            CandidateCampaign.objects.bulk_update(update_list, ['seo_friendly_path'])
            messages.add_message(request, messages.INFO,
                                 "{updates_made:,} candidates updated with new seo_friendly_path."
                                 "".format(updates_made=updates_made))
        if len(candidates_to_update_from_politician) > 0:
            from candidate.controllers import update_candidate_details_from_politician
            for candidate in candidates_to_update_from_politician:
                results = update_candidate_details_from_politician(candidate=candidate, politician=politician_on_stage)
                if results['success'] and results['save_changes']:
                    candidate_to_update = results['candidate']
                    candidate_to_update.save()
                else:
                    status += results['status']

    # Update Linked Representatives with seo_friendly_path
    if success and positive_value_exists(politician_on_stage.seo_friendly_path) and push_seo_friendly_path_changes:
        representative_manager = RepresentativeManager()
        politician_we_vote_id_list = [politician_we_vote_id]
        representative_results = representative_manager.retrieve_representative_list(
            politician_we_vote_id_list=politician_we_vote_id_list,
        )
        if not representative_results['success']:
            status += representative_results['status']
            status += "FAILED_TO_RETRIEVE_REPRESENTATIVES_LINKED_TO_POLITICIAN "
            messages.add_message(request, messages.ERROR, status)
        update_list = []
        updates_needed = False
        updates_made = 0
        if representative_results['representative_list_found']:
            representative_list = representative_results['representative_list']
            for representative in representative_list:
                representative.seo_friendly_path = politician_on_stage.seo_friendly_path
                update_list.append(representative)
                updates_needed = True
                updates_made += 1
        if updates_needed:
            Representative.objects.bulk_update(update_list, ['seo_friendly_path'])
            messages.add_message(request, messages.INFO,
                                 "{updates_made:,} representatives updated with new seo_friendly_path."
                                 "".format(updates_made=updates_made))

    # Update Linked CampaignX with seo_friendly_path (Only if hard-linked)
    if success and positive_value_exists(politician_on_stage.linked_campaignx_we_vote_id) \
            and positive_value_exists(politician_on_stage.seo_friendly_path) and push_seo_friendly_path_changes:
        # TODO Implement this
        pass

    # ####################################################################
    # To make sure we have the freshest data, update supporters_count on all objects
    if positive_value_exists(politician_on_stage.linked_campaignx_we_vote_id):
        from campaign.controllers import create_campaignx_supporters_from_positions, \
            refresh_campaignx_supporters_count_in_all_children
        campaignx_we_vote_id_list_to_refresh = [politician_on_stage.linked_campaignx_we_vote_id]
        politician_we_vote_id_list = [politician_on_stage.we_vote_id]
        # #############################
        # Create campaignx_supporters
        create_from_friends_only_positions = False
        results = create_campaignx_supporters_from_positions(
            request,
            friends_only_positions=False,
            politician_we_vote_id_list=politician_we_vote_id_list)
        campaignx_we_vote_id_list_changed = results['campaignx_we_vote_id_list_to_refresh']
        if len(campaignx_we_vote_id_list_changed) > 0:
            campaignx_we_vote_id_list_to_refresh = \
                list(set(campaignx_we_vote_id_list_changed + campaignx_we_vote_id_list_to_refresh))
        if not positive_value_exists(results['campaignx_supporter_entries_created']):
            create_from_friends_only_positions = True
        if create_from_friends_only_positions:
            results = create_campaignx_supporters_from_positions(
                request,
                friends_only_positions=True,
                politician_we_vote_id_list=politician_we_vote_id_list)
            campaignx_we_vote_id_list_changed = results['campaignx_we_vote_id_list_to_refresh']
            if len(campaignx_we_vote_id_list_changed) > 0:
                campaignx_we_vote_id_list_to_refresh = \
                    list(set(campaignx_we_vote_id_list_changed + campaignx_we_vote_id_list_to_refresh))

        campaignx_manager = CampaignXManager()
        supporter_count = campaignx_manager.fetch_campaignx_supporter_count(
            politician_on_stage.linked_campaignx_we_vote_id)
        results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=politician_on_stage.linked_campaignx_we_vote_id)
        if results['campaignx_found']:
            campaignx = results['campaignx']
            campaignx.supporters_count = supporter_count
            campaignx.save()

        results = refresh_campaignx_supporters_count_in_all_children(
            request,
            campaignx_we_vote_id_list=campaignx_we_vote_id_list_to_refresh)
        if positive_value_exists(results['update_message']):
            update_message += results['update_message']

    # ##################################################
    # Change log and volunteer scoring
    if change_description_changed:
        voter_manager = VoterManager()
        voter_api_device_id = get_voter_api_device_id(request)
        results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id, read_only=True)
        voter_full_name = ''
        voter_id = ''
        voter_we_vote_id = ''
        if results['voter_found']:
            voter_on_stage = results['voter']
            voter_full_name = voter_on_stage.get_full_name(real_name_only=True)
            voter_id = voter_on_stage.id
            voter_we_vote_id = voter_on_stage.we_vote_id

        from volunteer_task.controllers import is_candidate_or_politician_analysis_done
        if positive_value_exists(candidate_analysis_comment) \
                or is_candidate_or_politician_analysis_done(changes_found_dict=changes_found_dict):
            kind_of_log_entry = KIND_OF_LOG_ENTRY_ANALYSIS_COMMENT
        else:
            kind_of_log_entry = KIND_OF_LOG_ENTRY_LINK_ADDED
        results = politician_manager.create_politician_log_entry(
            politician_we_vote_id=politician_we_vote_id,
            change_description=change_description,
            changes_found_dict=changes_found_dict,
            changed_by_name=voter_full_name,
            changed_by_voter_we_vote_id=voter_we_vote_id,
            kind_of_log_entry=kind_of_log_entry,
        )
        # Now add to the volunteers scores for doing tasks
        if positive_value_exists(voter_we_vote_id):
            # Give the volunteer who entered this credit
            from volunteer_task.controllers import augmentation_change_found
            from volunteer_task.models import VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION, \
                VOLUNTEER_ACTION_POLITICIAN_REQUEST, VOLUNTEER_ACTION_POLITICIAN_PHOTO
            if augmentation_change_found(changes_found_dict=changes_found_dict):
                try:
                    task_results = volunteer_task_manager.create_volunteer_task_completed(
                        action_constant=VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION,
                        voter_id=voter_id,
                        voter_we_vote_id=voter_we_vote_id,
                    )
                except Exception as e:
                    status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED-AUGMENTATION: ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            from volunteer_task.controllers import politician_requested_change_found
            if politician_requested_change_found(changes_found_dict=changes_found_dict):
                try:
                    task_results = volunteer_task_manager.create_volunteer_task_completed(
                        action_constant=VOLUNTEER_ACTION_POLITICIAN_REQUEST,
                        voter_id=voter_id,
                        voter_we_vote_id=voter_we_vote_id,
                    )
                except Exception as e:
                    status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED-POLITICIAN_REQUEST: ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            from volunteer_task.controllers import photo_change_found
            if photo_change_found(changes_found_dict=changes_found_dict):
                try:
                    task_results = volunteer_task_manager.create_volunteer_task_completed(
                        action_constant=VOLUNTEER_ACTION_POLITICIAN_PHOTO,
                        voter_id=voter_id,
                        voter_we_vote_id=voter_we_vote_id,
                    )
                except Exception as e:
                    status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED-PHOTO: ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    if positive_value_exists(update_message):
        messages.add_message(request, messages.INFO, update_message)

    if politician_id:
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))
    else:
        return HttpResponseRedirect(reverse('politician:politician_new', args=()))


@login_required
def politician_retrieve_photos_view(request, candidate_id):  # TODO DALE Transition fully to politician
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
def politician_delete_process_view(request):
    """
    Delete this politician
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician_id = convert_to_int(request.GET.get('politician_id', 0))

    # Retrieve this politician
    politician_we_vote_id = ''
    politician_on_stage_found = False
    politician_on_stage = None
    if positive_value_exists(politician_id):
        try:
            politician_query = Politician.objects.filter(id=politician_id)
            if len(politician_query):
                politician_on_stage = politician_query[0]
                politician_we_vote_id = politician_on_stage.we_vote_id
                politician_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find politician -- exception: ', str(e))

    if not politician_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find politician.')
        return HttpResponseRedirect(reverse('politician:politician_list', args=()))

    # Are there any positions attached to this politician that should be moved to another instance of this politician?
    if positive_value_exists(politician_id) or positive_value_exists(politician_we_vote_id):
        position_list_manager = PositionListManager()
        candidate_list_manager = CandidateListManager()
        # By not passing in new values, we remove politician_id and politician_we_vote_id
        results = position_list_manager.update_politician_we_vote_id_in_all_positions(
            politician_id=politician_id,
            politician_we_vote_id=politician_we_vote_id)
        results = candidate_list_manager.update_politician_we_vote_id_in_all_candidates(
            politician_id=politician_id,
            politician_we_vote_id=politician_we_vote_id)

    try:
        # Delete the politician
        politician_on_stage.delete()
        messages.add_message(request, messages.INFO, 'Politician deleted.')
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete politician -- exception: ' + str(e))
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))

    return HttpResponseRedirect(reverse('politician:politician_list', args=()))


# This page does not need to be protected.
def politicians_sync_out_view(request):  # politiciansSyncOut
    status = ""
    state_code = request.GET.get('state_code', '')
    politician_search = request.GET.get('politician_search', '')

    try:
        politician_query = Politician.objects.using('readonly').all()
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        filters = []
        if positive_value_exists(politician_search):
            new_filter = Q(politician_name__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_twitter_handle__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_twitter_handle2__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_twitter_handle3__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_twitter_handle4__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_twitter_handle5__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_url__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_url2__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_url3__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_url4__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_url5__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(party__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=politician_search)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                politician_query = politician_query.filter(final_filters)

        politician_query = politician_query.values(
            'we_vote_id',
            'ballotpedia_id',
            'ballotpedia_politician_name',
            'ballotpedia_politician_url',
            'bioguide_id',
            'birth_date',
            'cspan_id',
            'ctcl_uuid',
            'date_last_updated',
            'date_last_updated_from_candidate',
            'facebook_url',
            'facebook_url2',
            'facebook_url3',
            'facebook_url_is_broken',
            'facebook_url2_is_broken',
            'facebook_url3_is_broken',
            'fec_id',
            'first_name',
            'full_name_assembled',
            'gender',
            'google_civic_candidate_name',
            'google_civic_candidate_name2',
            'google_civic_candidate_name3',
            'govtrack_id',
            'house_history_id',
            'icpsr_id',
            'instagram_followers_count',
            'instagram_handle',
            'is_battleground_race_2019',
            'is_battleground_race_2020',
            'is_battleground_race_2021',
            'is_battleground_race_2022',
            'is_battleground_race_2023',
            'is_battleground_race_2024',
            'is_battleground_race_2025',
            'is_battleground_race_2026',
            'last_name',
            'linked_campaignx_we_vote_id',
            'linkedin_url',
            'lis_id',
            'maplight_id',
            'middle_name',
            'opensecrets_id',
            'political_party',
            'politician_contact_form_url',
            'politician_email_address',
            'politician_email',
            'politician_email2',
            'politician_email3',
            'politician_facebook_id',
            'politician_googleplus_id',
            'politician_name',
            'politician_phone_number',
            'politician_phone_number2',
            'politician_phone_number3',
            'politician_twitter_handle',
            'politician_twitter_handle2',
            'politician_twitter_handle3',
            'politician_twitter_handle4',
            'politician_twitter_handle5',
            'politician_url',
            'politician_url2',
            'politician_url3',
            'politician_url4',
            'politician_url5',
            'politician_youtube_id',
            'profile_image_background_color',
            'profile_image_type_currently_active',
            'seo_friendly_path',
            'seo_friendly_path_date_last_updated',
            'state_code',
            'thomas_id',
            'twitter_description',
            'twitter_followers_count',
            'twitter_handle_updates_failing',
            'twitter_handle2_updates_failing',
            'twitter_location',
            'twitter_name',
            'twitter_profile_image_url_https',
            'twitter_profile_background_image_url_https',
            'twitter_profile_banner_url_https',
            'twitter_user_id',
            'vote_smart_id',
            'vote_usa_politician_id',
            'vote_usa_profile_image_url_https',
            'washington_post_id',
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
            'wikipedia_id',
            'wikipedia_url',
            'youtube_url')
        if politician_query:
            modified_politician_dict_list = []
            politician_dict_list = list(politician_query)
            for one_dict in politician_dict_list:
                birth_date = one_dict.get('birth_date', '')
                if positive_value_exists(birth_date):
                    one_dict['birth_date'] = birth_date.strftime('%Y-%m-%d')
                date_last_updated = one_dict.get('date_last_updated', '')
                if positive_value_exists(date_last_updated):
                    one_dict['date_last_updated'] = date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
                date_last_updated_from_candidate = one_dict.get('date_last_updated_from_candidate', '')
                if positive_value_exists(date_last_updated_from_candidate):
                    one_dict['date_last_updated_from_candidate'] = \
                        date_last_updated_from_candidate.strftime('%Y-%m-%d %H:%M:%S')
                seo_friendly_path_date_last_updated = one_dict.get('seo_friendly_path_date_last_updated', '')
                if positive_value_exists(seo_friendly_path_date_last_updated):
                    one_dict['seo_friendly_path_date_last_updated'] = \
                        seo_friendly_path_date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
                modified_politician_dict_list.append(one_dict)
            politician_list_json = list(modified_politician_dict_list)
            return HttpResponse(json.dumps(politician_list_json), content_type='application/json')
    except Exception as e:
        status += "POLITICIAN_LIST_MISSING: " + str(e) + " "

    json_data = {
        'success': False,
        'status': status
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def repair_ocd_id_mismatch_damage_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    politician_we_vote_id_list = []
    politicians_dict = {}

    politician_error_count = 0
    politician_list_count = 0
    states_already_match_count = 0
    states_fixed_count = 0
    states_to_be_fixed_count = 0
    status = ''
    try:
        queryset = Politician.objects.using('readonly').all()
        queryset = queryset.filter(ocd_id_state_mismatch_found=True)
        politician_data_list = list(queryset[:1000])
        politician_list_count = len(politician_data_list)
        for one_politician in politician_data_list:
            # Now find all representative ids related to this politician
            try:
                queryset = Representative.objects.all()
                queryset = queryset.filter(politician_we_vote_id__iexact=one_politician.we_vote_id)
                linked_representative_list = list(queryset)
                linked_representative = linked_representative_list[0]  # For now, just take the first one
                if positive_value_exists(linked_representative.ocd_division_id) and \
                        positive_value_exists(one_politician.state_code):
                    # Is there a mismatch between the ocd_id and the politician.state_code?
                    state_code_from_ocd_id = extract_state_from_ocd_division_id(linked_representative.ocd_division_id)
                    if not positive_value_exists(state_code_from_ocd_id):
                        # Cannot compare
                        pass
                    elif one_politician.state_code.lower() == state_code_from_ocd_id.lower():
                        # Already ok
                        states_already_match_count += 1
                    else:
                        # Fix
                        states_to_be_fixed_count += 1
                        one_politician.state_code = state_code_from_ocd_id
                        one_politician.seo_friendly_path = None
                        one_politician.seo_friendly_path_date_last_updated = now()
                        one_politician.save()
                        states_fixed_count += 1
            except Exception as e:
                politician_error_count += 1
                if politician_error_count < 10:
                    status += "COULD_NOT_SAVE_POLITICIAN: " + str(e) + " "
            politicians_dict[one_politician.we_vote_id] = one_politician
            politician_we_vote_id_list.append(one_politician.we_vote_id)
    except Exception as e:
        status += "GENERAL_ERROR: " + str(e) + " "

    messages.add_message(request, messages.INFO,
                         "Politicians analyzed: {politician_list_count:,}. "
                         "states_already_match_count: {states_already_match_count:,}. "
                         "states_to_be_fixed_count: {states_to_be_fixed_count} "
                         "status: {status}"
                         "".format(
                             politician_list_count=politician_list_count,
                             states_already_match_count=states_already_match_count,
                             states_to_be_fixed_count=states_to_be_fixed_count,
                             status=status))

    return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                "?google_civic_election_id={google_civic_election_id}"
                                "&state_code={state_code}"
                                "&show_ocd_id_state_mismatch=1"
                                "".format(
                                    google_civic_election_id=google_civic_election_id,
                                    state_code=state_code))


@login_required
def update_politician_from_candidate_view(request):
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')
    politician_id = request.GET.get('politician_id', 0)
    politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
    if not positive_value_exists(politician_id) and not positive_value_exists(politician_we_vote_id):
        message = "Unable to update politician from candidate. Missing politician_id and we_vote_id."
        messages.add_message(request, messages.INFO, message)
        return HttpResponseRedirect(reverse('politician:politician_list', args=()))

    if positive_value_exists(politician_we_vote_id):
        politician = Politician.objects.get(we_vote_id=politician_we_vote_id)
    else:
        politician = Politician.objects.get(id=politician_id)
    politician_id = politician.id
    politician_we_vote_id = politician.we_vote_id

    queryset = CandidateCampaign.objects.using('readonly').all()
    queryset = queryset.filter(politician_we_vote_id__iexact=politician_we_vote_id)
    if positive_value_exists(candidate_we_vote_id):
        queryset = queryset.filter(we_vote_id__iexact=candidate_we_vote_id)
    queryset = queryset.order_by('-candidate_year', '-candidate_ultimate_election_date')
    candidate_list = list(queryset)
    candidate_list_by_politician_we_vote_id = {}
    for one_candidate in candidate_list:
        # Only put the first one in
        if one_candidate.politician_we_vote_id not in candidate_list_by_politician_we_vote_id:
            candidate_list_by_politician_we_vote_id[one_candidate.politician_we_vote_id] = one_candidate

    if politician.we_vote_id in candidate_list_by_politician_we_vote_id:
        candidate = candidate_list_by_politician_we_vote_id[politician.we_vote_id]
        results = update_politician_details_from_candidate(politician=politician, candidate=candidate)
        if results['success']:
            save_changes = results['save_changes']
            politician = results['politician']
            if save_changes:
                politician.date_last_updated_from_candidate = localtime(now()).date()
                politician.save()
                message = "Politician updated."
                messages.add_message(request, messages.INFO, message)
            else:
                message = "Politician not updated. No changes found."
                messages.add_message(request, messages.INFO, message)
        else:
            message = "Politician not updated. Error: " + str(results['status'])
            messages.add_message(request, messages.INFO, message)
    else:
        message = "Politician not updated. No candidates found to update politician from."
        messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))


@login_required
def update_politicians_from_candidates_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    success = True
    state_code = request.GET.get('state_code', "")

    politician_list = []
    try:
        queryset = Politician.objects.all()
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        # Ignore politicians who have been updated in the last 6 months: date_last_updated_from_politician
        today = datetime.now().date()
        six_months = timedelta(weeks=26)
        six_months_ago = today - six_months
        queryset = queryset.exclude(date_last_updated_from_candidate__gt=six_months_ago)
        politician_list = list(queryset[:3000])
    except Exception as e:
        status += "REPRESENTATIVE_QUERY_FAILED: " + str(e) + " "

    # Retrieve all related candidates with one query
    politician_we_vote_id_list = []
    for politician in politician_list:
        if positive_value_exists(politician.we_vote_id):
            if politician.we_vote_id not in politician_we_vote_id_list:
                politician_we_vote_id_list.append(politician.we_vote_id)

    candidate_list_by_politician_we_vote_id = {}
    if len(politician_we_vote_id_list) > 0:
        queryset = CandidateCampaign.objects.all()
        queryset = queryset.filter(politician_we_vote_id__in=politician_we_vote_id_list)
        queryset = queryset.order_by('-candidate_year', '-candidate_ultimate_election_date')
        candidate_list = list(queryset)
        for one_candidate in candidate_list:
            # Only put the first one in
            if one_candidate.politician_we_vote_id not in candidate_list_by_politician_we_vote_id:
                candidate_list_by_politician_we_vote_id[one_candidate.politician_we_vote_id] = one_candidate

    # Loop through all the politicians in this year, and update them with some politician data
    politician_update_errors = 0
    politicians_updated = 0
    politicians_without_changes = 0
    for we_vote_politician in politician_list:
        if we_vote_politician.we_vote_id in candidate_list_by_politician_we_vote_id:
            candidate = candidate_list_by_politician_we_vote_id[we_vote_politician.we_vote_id]
        else:
            candidate = None
            we_vote_politician.date_last_updated_from_candidate = localtime(now()).date()
            we_vote_politician.save()
        if not candidate or not hasattr(candidate, 'we_vote_id'):
            continue
        results = update_politician_details_from_candidate(politician=we_vote_politician, candidate=candidate)
        if results['success']:
            save_changes = results['save_changes']
            we_vote_politician = results['politician']
            we_vote_politician.date_last_updated_from_candidate = localtime(now()).date()
            we_vote_politician.save()
            if save_changes:
                politicians_updated += 1
            else:
                politicians_without_changes += 1
        else:
            politician_update_errors += 1
            status += results['status']

    message = \
        "Politicians updated: {politicians_updated:,}. " \
        "Politicians without changes: {politicians_without_changes:,}. " \
        "Politician update errors: {politician_update_errors:,}. " \
        "".format(
            politician_update_errors=politician_update_errors,
            politicians_updated=politicians_updated,
            politicians_without_changes=politicians_without_changes)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                "?state_code={state_code}"
                                "".format(
                                    state_code=state_code))


def update_profile_image_background_color_view_for_politicians(request):
    number_to_update = 5000
    politician_query = Politician.objects.all()
    state_code = request.GET.get('state_code', '')
    if positive_value_exists(state_code):
        politician_query = politician_query.filter(state_code__iexact=state_code)
    politician_query = politician_query.exclude(profile_image_background_color_needed=False)
    politician_list_count = politician_query.count()
    politician_list = list(politician_query[:number_to_update])
    message = ''
    if politician_list_count == 0:
        message += "All politicians have been updated with a background color for profile photo."
        messages.add_message(request, messages.INFO, message)
    else:
        message += "{count:,} politicians need a background color for profile photo. ".format(count=politician_list_count)

    bulk_update_list = []
    politicians_updated = 0
    politicians_not_updated = 0
    for politician in politician_list:
        politician.profile_image_background_color_needed = False
        if positive_value_exists(politician.we_vote_hosted_profile_image_url_large):
            hex = generate_background(politician)
            politician.profile_image_background_color = hex
            politicians_updated += 1
        else:
            politicians_not_updated += 1
        bulk_update_list.append(politician)
    try:
        Politician.objects.bulk_update(
            bulk_update_list,
            ['profile_image_background_color', 'profile_image_background_color_needed'])
        message += \
            "Politicians updated: {politicians_updated:,}. " \
            "Politicians without picture URL:  {politicians_not_updated:,}. " \
            "".format(politicians_updated=politicians_updated, politicians_not_updated=politicians_not_updated)
        messages.add_message(request, messages.INFO, message)
    except Exception as e:
        messages.add_message(request, messages.ERROR,
                             "ERROR with update_profile_image_background_color_view: {e}"
                             "".format(e=e))

    return HttpResponseRedirect(reverse('politician:politician_list', args=()))


def update_recommended_politicians_view(request):
    """
       Update recommended politicians based on certain criteria.
       This view function updates the recommended politicians by performing several operations such as clustering,
       one-hot encoding, TF-IDF, and adding clusters. It then selects politicians from the same cluster and a few from
       outside the cluster as recommendations.
       Parameters:
       - request: Django HttpRequest object
       Returns:
       - HttpResponseRedirect: Redirects to the politician list page with a specified state code.
       """

    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    success = True
    state_code = request.GET.get('state_code', "")

    try:
        RecommendedPoliticianLinkByPolitician.objects.all().delete()
        update_recommend()
    except Exception as e:
        status += "Could not update: " + str(e) + " "

    validation_list = []
    sample_num = 100
    for _ in range(sample_num):
        random_politician = Politician.objects.order_by('?').first()
        record = Politician.get_recommendation(random_politician)
        validation_list.extend(record)

    message = \
        "avg recommended number : {politicians_avgs:,}. " \
        "".format(
            politicians_avgs=len(validation_list) / sample_num)
    messages.add_message(request, messages.INFO, message)
    return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                "?state_code={state_code}"
                                "".format(state_code=state_code))
