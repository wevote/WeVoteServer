# position/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import generate_position_sorting_dates_for_election, positions_import_from_master_server, \
    refresh_cached_position_info_for_election, \
    refresh_positions_with_candidate_details_for_election, \
    refresh_positions_with_contest_office_details_for_election, \
    refresh_positions_with_contest_measure_details_for_election
from .models import ANY_STANCE, PositionEntered, PositionForFriends, PositionListManager, PERCENT_RATING
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaign, CandidateListManager, CandidateManager
from config.base import get_environment_variable
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.db.models import Q
from election.controllers import retrieve_election_id_list_by_year_list
from election.models import ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from measure.controllers import push_contest_measure_data_to_other_table_caches
from office.controllers import push_contest_office_data_to_other_table_caches
from office.models import ContestOfficeManager
from organization.models import OrganizationManager
from politician.models import PoliticianManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, convert_integer_to_string_with_comma_for_thousands_separator, \
    positive_value_exists, STATE_CODE_MAP
from wevote_settings.constants import ELECTION_YEARS_AVAILABLE
from django.http import HttpResponse
import json

UNKNOWN = 'U'
POSITIONS_SYNC_URL = get_environment_variable("POSITIONS_SYNC_URL")  # positionsSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
def positions_sync_out_view(request):  # positionsSyncOut
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    if not positive_value_exists(google_civic_election_id):
        json_data = {
            'success': False,
            'status': 'POSITION_LIST_CANNOT_BE_RETURNED-ELECTION_ID_REQUIRED'
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    stance_we_are_looking_for = ANY_STANCE
    try:
        # Only return public positions
        position_list_query = PositionEntered.objects.order_by('date_entered')

        # As of Aug 2018 we are no longer using PERCENT_RATING
        position_list_query = position_list_query.exclude(stance__iexact=PERCENT_RATING)

        position_list_query = position_list_query.filter(google_civic_election_id=google_civic_election_id)
        # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
        if stance_we_are_looking_for != ANY_STANCE:
            # If we passed in the stance "ANY" it means we want to not filter down the list
            position_list_query = position_list_query.filter(stance__iexact=stance_we_are_looking_for)

        # convert datetime to str for date_entered and date_last_changed columns
        position_list_query = position_list_query.extra(
            select={'date_entered': "to_char(date_entered, 'YYYY-MM-DD HH24:MI:SS')"})
        position_list_query = position_list_query.extra(
            select={'date_last_changed': "to_char(date_last_changed, 'YYYY-MM-DD HH24:MI:SS')"})

        position_list_dict = position_list_query.values(
            'we_vote_id', 'ballot_item_display_name', 'ballot_item_image_url_https',
            'ballot_item_twitter_handle', 'speaker_display_name',
            'speaker_image_url_https', 'speaker_twitter_handle', 'date_entered',
            'date_last_changed', 'organization_we_vote_id', 'voter_we_vote_id',
            'public_figure_we_vote_id', 'google_civic_election_id', 'state_code',
            'vote_smart_rating_id', 'vote_smart_time_span', 'vote_smart_rating',
            'vote_smart_rating_name', 'contest_office_we_vote_id', 'race_office_level',
            'candidate_campaign_we_vote_id', 'google_civic_candidate_name',
            'politician_we_vote_id', 'contest_measure_we_vote_id', 'speaker_type', 'stance',
            'position_ultimate_election_date', 'position_year',
            'statement_text', 'statement_html', 'twitter_followers_count', 'more_info_url', 'from_scraper',
            'organization_certified', 'volunteer_certified', 'voter_entering_position',
            'tweet_source_id', 'twitter_user_entered_position', 'is_private_citizen')

        if position_list_dict:
            position_list_json = list(position_list_dict)
            return HttpResponse(json.dumps(position_list_json), content_type='application/json')
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    json_data = {
        'success': False,
        'status': 'POSITION_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def positions_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in POSITIONS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.INFO, 'Google civic election id is required for Positions import.')
        return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                    str(google_civic_election_id) + "&state_code=" + str(state_code))

    results = positions_import_from_master_server(request, google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Positions import completed. '
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


def update_position_list_with_speaker_type(position_list):
    organization_manager = OrganizationManager()
    organization_dict = {}
    for one_position in position_list:
        position_change = False
        speaker_type = UNKNOWN
        twitter_followers_count = 0
        if one_position.organization_we_vote_id in organization_dict:
            organization = organization_dict[one_position.organization_we_vote_id]
            speaker_type = organization.organization_type
            twitter_followers_count = organization.twitter_followers_count
        else:
            organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                one_position.organization_we_vote_id)
            if organization_results['organization_found']:
                organization = organization_results['organization']
                organization_dict[one_position.organization_we_vote_id] = organization
                speaker_type = organization.organization_type
                twitter_followers_count = organization.twitter_followers_count
        if speaker_type != UNKNOWN:
            one_position.speaker_type = speaker_type
            position_change = True
        if positive_value_exists(twitter_followers_count):
            one_position.twitter_followers_count = twitter_followers_count
            position_change = True
        if position_change:
            one_position.save()
    return True


def update_position_list_with_contest_office_info(position_list):
    candidate_manager = CandidateManager()
    candidate_dict = {}
    politician_manager = PoliticianManager()
    politician_dict = {}
    for one_position in position_list:
        candidate_id = 0
        contest_office_we_vote_id = ''
        contest_office_id = 0
        politician_we_vote_id = ''
        politician_id = 0
        position_change = False
        if one_position.candidate_campaign_we_vote_id in candidate_dict:
            candidate = candidate_dict[one_position.candidate_campaign_we_vote_id]
            candidate_id = candidate.id
            contest_office_we_vote_id = candidate.contest_office_we_vote_id
            contest_office_id = candidate.contest_office_id
            politician_we_vote_id = candidate.politician_we_vote_id
            politician_id = candidate.politician_id
        else:
            results = candidate_manager.retrieve_candidate_from_we_vote_id(
                one_position.candidate_campaign_we_vote_id, read_only=False)  # May be able to be read_only
            if results['candidate_found']:
                candidate = results['candidate']
                candidate_dict[one_position.candidate_campaign_we_vote_id] = candidate
                candidate_id = candidate.id
                contest_office_we_vote_id = candidate.contest_office_we_vote_id
                contest_office_id = candidate.contest_office_id
                politician_we_vote_id = candidate.politician_we_vote_id
                politician_id = candidate.politician_id
        if positive_value_exists(candidate_id):
            one_position.candidate_campaign_id = candidate_id
            position_change = True
        if positive_value_exists(contest_office_we_vote_id):
            one_position.contest_office_we_vote_id = contest_office_we_vote_id
            position_change = True
        if positive_value_exists(contest_office_id):
            one_position.contest_office_id = contest_office_id
            position_change = True
        if positive_value_exists(politician_we_vote_id):
            one_position.politician_we_vote_id = politician_we_vote_id
            position_change = True
        if positive_value_exists(politician_id):
            one_position.politician_id = politician_id
            position_change = True
        elif positive_value_exists(politician_we_vote_id):
            # Look up the politician_id
            if politician_we_vote_id in politician_dict:
                politician = politician_dict[politician_we_vote_id]
                one_position.politician_id = politician.id
                position_change = True
            else:
                results = politician_manager.retrieve_politician(0, politician_we_vote_id)
                if results['politician_found']:
                    politician = results['politician']
                    politician_dict[politician_we_vote_id] = politician
                    one_position.politician_id = politician.id
                    position_change = True
        if position_change:
            one_position.save()
    return True


@login_required
def position_list_view(request):
    """
    We actually don't want to see PositionForFriends entries in this view
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    show_statistics = positive_value_exists(request.GET.get('show_statistics', False))
    show_this_year_of_elections = convert_to_int(request.GET.get('show_this_year_of_elections', 0))
    state_code = request.GET.get('state_code', '')
    state_list = STATE_CODE_MAP
    state_list_modified = {}

    position_search = request.GET.get('position_search', '')

    candidate_list_manager = CandidateListManager()
    election_manager = ElectionManager()
    google_civic_election_id_list_for_dropdown = []
    if positive_value_exists(show_this_year_of_elections):
        election_year_list_to_show = [show_this_year_of_elections]
        google_civic_election_id_list_for_dropdown = \
            retrieve_election_id_list_by_year_list(election_year_list_to_show=election_year_list_to_show)
    elif positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        temp_election_list = results['election_list']
        for one_election in temp_election_list:
            google_civic_election_id_list_for_dropdown.append(one_election.google_civic_election_id)
    else:
        results = election_manager.retrieve_upcoming_elections()
        temp_election_list = results['election_list']

        # Make sure we always include the current election in the election_list, even if it is older
        if positive_value_exists(google_civic_election_id):
            this_election_found = False
            for one_election in temp_election_list:
                if convert_to_int(one_election.google_civic_election_id) == convert_to_int(google_civic_election_id):
                    this_election_found = True
                    break
            if not this_election_found:
                results = election_manager.retrieve_election(google_civic_election_id)
                if results['election_found']:
                    one_election = results['election']
                    temp_election_list.append(one_election)

        for one_election in temp_election_list:
            google_civic_election_id_list_for_dropdown.append(one_election.google_civic_election_id)

    if positive_value_exists(google_civic_election_id):
        google_civic_election_id_list_for_display = [google_civic_election_id]
    elif positive_value_exists(show_this_year_of_elections):
        google_civic_election_id_list_for_display = google_civic_election_id_list_for_dropdown
    elif positive_value_exists(show_all_elections):
        google_civic_election_id_list_for_display = google_civic_election_id_list_for_dropdown
    else:
        google_civic_election_id_list_for_display = google_civic_election_id_list_for_dropdown

    if len(google_civic_election_id_list_for_display) > 0:
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list_for_display,
            limit_to_this_state_code=state_code)
        if not positive_value_exists(results['success']):
            success = False
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']
    else:
        candidate_we_vote_id_list = []

    public_position_list_clean_count = 0
    friend_position_list_clean_count = 0
    if positive_value_exists(show_statistics):
        # Make sure all positions in this election have a speaker_type
        if positive_value_exists(google_civic_election_id):
            public_position_list_clean_query = PositionEntered.objects.all()
            public_position_list_clean_query = public_position_list_clean_query.filter(
                Q(google_civic_election_id__in=google_civic_election_id_list_for_display) |
                Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
            public_position_list_clean_query = public_position_list_clean_query.filter(
                speaker_type=UNKNOWN,
            )
            public_position_list_clean_count_query = public_position_list_clean_query
            public_position_list_clean_count = public_position_list_clean_count_query.count()
            public_position_list_clean = list(public_position_list_clean_count_query)
            update_position_list_with_speaker_type(public_position_list_clean)

            friend_position_list_clean_query = PositionForFriends.objects.all()
            friend_position_list_clean_query = friend_position_list_clean_query.filter(
                Q(google_civic_election_id__in=google_civic_election_id_list_for_display) |
                Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
            friend_position_list_clean_query = friend_position_list_clean_query.filter(
                speaker_type=UNKNOWN,
            )
            friend_position_list_clean_count_query = friend_position_list_clean_query
            friend_position_list_clean_count = friend_position_list_clean_count_query.count()
            friend_position_list_clean = list(friend_position_list_clean_count_query)
            update_position_list_with_speaker_type(friend_position_list_clean)

    public_position_list_candidate_clean_count = 0
    friend_position_list_candidate_clean_count = 0
    if positive_value_exists(show_statistics):
        # Make sure all candidate-related positions in this election have contest_office information and politician info
        if positive_value_exists(google_civic_election_id):
            public_position_list_candidate_clean_query = PositionEntered.objects.all()
            public_position_list_candidate_clean_query = public_position_list_candidate_clean_query.filter(
                Q(google_civic_election_id__in=google_civic_election_id_list_for_display) |
                Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
            public_position_list_candidate_clean_query = public_position_list_candidate_clean_query.exclude(
                Q(candidate_campaign_we_vote_id__isnull=True) | Q(candidate_campaign_we_vote_id=""))
            public_position_list_candidate_clean_count_query = public_position_list_candidate_clean_query
            public_position_list_candidate_clean_count = public_position_list_candidate_clean_count_query.count()
            public_position_list_candidate_clean = list(public_position_list_candidate_clean_count_query)
            update_position_list_with_contest_office_info(public_position_list_candidate_clean)

            friend_position_list_candidate_clean_query = PositionForFriends.objects.all()
            friend_position_list_candidate_clean_query = friend_position_list_candidate_clean_query.filter(
                Q(google_civic_election_id__in=google_civic_election_id_list_for_display) |
                Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
            friend_position_list_candidate_clean_query = friend_position_list_candidate_clean_query.exclude(
                Q(candidate_campaign_we_vote_id__isnull=True) | Q(candidate_campaign_we_vote_id=""))
            friend_position_list_candidate_clean_count_query = friend_position_list_candidate_clean_query
            friend_position_list_candidate_clean_count = friend_position_list_candidate_clean_count_query.count()
            friend_position_list_candidate_clean = list(friend_position_list_candidate_clean_count_query)
            update_position_list_with_contest_office_info(friend_position_list_candidate_clean)

    # Publicly visible positions
    public_position_list_query = PositionEntered.objects.order_by('-id')  # This order_by is temp
    public_position_list_query = public_position_list_query.exclude(stance__iexact=PERCENT_RATING)
    public_position_list_query = public_position_list_query.filter(
        Q(google_civic_election_id__in=google_civic_election_id_list_for_display) |
        Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
    if positive_value_exists(state_code):
        public_position_list_query = public_position_list_query.filter(state_code__iexact=state_code)

    if positive_value_exists(position_search):
        search_words = position_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(state_code__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(candidate_campaign_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(contest_measure_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(contest_office_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(voter_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_measure_title__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(speaker_display_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(ballot_item_display_name__icontains=one_word)
            filters.append(new_filter)

            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                public_position_list_query = public_position_list_query.filter(final_filters)

    public_position_list_count = 0
    public_position_list_comments_count = 0
    if positive_value_exists(show_statistics):
        public_position_list_count_query = public_position_list_query
        public_position_list_count = public_position_list_count_query.count()

        public_position_list_comments_count_query = public_position_list_query
        public_position_list_comments_count_query = public_position_list_comments_count_query.exclude(
            (Q(statement_text__isnull=True) | Q(statement_text__exact='')))
        public_position_list_comments_count = public_position_list_comments_count_query.count()

    public_position_list_query = public_position_list_query[:10]
    public_position_list = list(public_position_list_query)

    # Friends-only visible positions
    friends_only_position_list_query = PositionForFriends.objects.order_by('-id')  # This order_by is temp
    # As of Aug 2018 we are no longer using PERCENT_RATING
    friends_only_position_list_query = friends_only_position_list_query.exclude(stance__iexact=PERCENT_RATING)
    friends_only_position_list_query = friends_only_position_list_query.filter(
        Q(google_civic_election_id__in=google_civic_election_id_list_for_display) |
        Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
    if positive_value_exists(state_code):
        friends_only_position_list_query = friends_only_position_list_query.filter(state_code__iexact=state_code)

    if positive_value_exists(position_search):
        search_words = position_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(state_code__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(candidate_campaign_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(contest_measure_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            # new_filter = Q(contest_office_name__icontains=one_word)
            # filters.append(new_filter)
            #
            # new_filter = Q(contest_office_we_vote_id__iexact=one_word)
            # filters.append(new_filter)

            new_filter = Q(organization_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(voter_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_measure_title__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(speaker_display_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(ballot_item_display_name__icontains=one_word)
            filters.append(new_filter)

            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                friends_only_position_list_query = friends_only_position_list_query.filter(final_filters)

    friends_only_position_list_count = 0
    friends_only_position_list_comments_count = 0
    if positive_value_exists(show_statistics):
        friends_only_position_list_count_query = friends_only_position_list_query
        friends_only_position_list_comments_count_query = friends_only_position_list_query
        friends_only_position_list_count = friends_only_position_list_count_query.count()

        friends_only_position_list_comments_count_query = friends_only_position_list_comments_count_query.exclude(
            (Q(statement_text__isnull=True) | Q(statement_text__exact='')))
        friends_only_position_list_comments_count = friends_only_position_list_comments_count_query.count()

    friends_only_position_list_query = friends_only_position_list_query[:10]
    friends_only_position_list = list(friends_only_position_list_query)

    position_list = public_position_list + friends_only_position_list

    if positive_value_exists(show_statistics):
        public_position_list_count_string = \
            convert_integer_to_string_with_comma_for_thousands_separator(public_position_list_count)
        public_position_list_comments_count_string = \
            convert_integer_to_string_with_comma_for_thousands_separator(public_position_list_comments_count)
        friends_only_position_list_count_string = \
            convert_integer_to_string_with_comma_for_thousands_separator(friends_only_position_list_count)
        friends_only_position_list_comments_count_string = \
            convert_integer_to_string_with_comma_for_thousands_separator(friends_only_position_list_comments_count)
        messages.add_message(
            request, messages.INFO,
            public_position_list_count_string + ' public positions found ' +
            '(' + public_position_list_comments_count_string + ' with commentary). ' +
            friends_only_position_list_count_string + ' friends-only positions found ' +
            '(' + friends_only_position_list_comments_count_string + ' with commentary). '
            )

        if public_position_list_clean_count or friend_position_list_clean_count:
            public_position_list_clean_count_string = \
                convert_integer_to_string_with_comma_for_thousands_separator(public_position_list_clean_count)
            friend_position_list_clean_count_string = \
                convert_integer_to_string_with_comma_for_thousands_separator(friend_position_list_clean_count)
            messages.add_message(
                request, messages.INFO,
                public_position_list_clean_count_string + ' public positions updated with speaker_type. ' +
                friend_position_list_clean_count_string + ' friends-only positions updated with speaker_type. '
            )

        if public_position_list_candidate_clean_count or friend_position_list_candidate_clean_count:
            public_position_list_candidate_clean_count_string = \
                convert_integer_to_string_with_comma_for_thousands_separator(public_position_list_candidate_clean_count)
            friend_position_list_candidate_clean_count_string = \
                convert_integer_to_string_with_comma_for_thousands_separator(friend_position_list_candidate_clean_count)
            messages.add_message(
                request, messages.INFO,
                public_position_list_candidate_clean_count_string + ' public positions updated with office info. ' +
                friend_position_list_candidate_clean_count_string + ' friends-only positions updated with office info. '
            )

    position_list_manager = PositionListManager()
    if len(google_civic_election_id_list_for_display) > 0:
        for one_state_code, one_state_name in state_list.items():
            state_name_modified = one_state_name
            if positive_value_exists(show_statistics):
                count_result = position_list_manager.retrieve_position_counts_for_election_and_state(
                    google_civic_election_id_list_for_display, one_state_code)
                if positive_value_exists(count_result['public_count']) \
                        or positive_value_exists(count_result['friends_only_count']):
                    state_name_modified += " - " + str(count_result['public_count']) + \
                                           '/' + str(count_result['friends_only_count'])
                else:
                    state_name_modified += ""
            state_list_modified[one_state_code] = state_name_modified

    sorted_state_list = sorted(state_list_modified.items())

    results = election_manager.retrieve_elections_by_google_civic_election_id_list(
        google_civic_election_id_list_for_dropdown, read_only=True)
    election_list = results['election_list']

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'position_list':            position_list,
        'position_search':          position_search,
        'election_list':            election_list,
        'election_years_available': ELECTION_YEARS_AVAILABLE,
        'google_civic_election_id': google_civic_election_id,
        'show_all_elections':       show_all_elections,
        'show_statistics':          show_statistics,
        'show_this_year_of_elections':  show_this_year_of_elections,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'position/position_list.html', template_values)


@login_required
def position_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'position/position_edit.html', template_values)


@login_required
def position_edit_view(request, position_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    position_on_stage_found = False
    try:
        position_on_stage = PositionEntered.objects.get(we_vote_id=position_we_vote_id)
        position_on_stage_found = True
    except PositionEntered.MultipleObjectsReturned as e:
        pass
    except PositionEntered.DoesNotExist:
        # This is fine, create new
        pass

    if position_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'position': position_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'position/position_edit.html', template_values)


@login_required
def position_edit_process_view(request):  # TODO DALE I don't think this is in use, but needs to be updated
    """
    Process the new or edit position forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    position_we_vote_id = request.POST.get('position_we_vote_id')
    position_name = request.POST['position_name']
    twitter_handle = request.POST['twitter_handle']
    position_website = request.POST['position_website']

    # Check to see if this position is already being used anywhere
    position_on_stage_found = False
    try:
        position_query = PositionEntered.objects.filter(we_vote_id=position_we_vote_id)
        if len(position_query):
            position_on_stage = position_query[0]
            position_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if position_on_stage_found:
            # Update
            position_on_stage.position_name = position_name
            position_on_stage.twitter_handle = twitter_handle
            position_on_stage.position_website = position_website
            position_on_stage.save()
            messages.add_message(request, messages.INFO, 'PositionEntered updated.')
        else:
            # Create new
            position_on_stage = CandidateCampaign(
                position_name=position_name,
                twitter_handle=twitter_handle,
                position_website=position_website,
            )
            position_on_stage.save()
            messages.add_message(request, messages.INFO, 'New position saved.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save position.')

    return HttpResponseRedirect(reverse('position:position_list', args=()))


@login_required
def position_summary_view(request, position_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    position_on_stage_found = False
    position_on_stage = PositionEntered()
    try:
        position_on_stage = PositionEntered.objects.get(we_vote_id=position_we_vote_id)
        position_on_stage_found = True
    except PositionEntered.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except PositionEntered.DoesNotExist:
        # This is fine, create new
        pass

    if position_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'position': position_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'position/position_summary.html', template_values)


@login_required
def refresh_cached_position_info_for_election_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = generate_position_sorting_dates_for_election(
        google_civic_election_id=google_civic_election_id)
    messages.add_message(
        request, messages.INFO,
        'candidate_to_office_link_update_count: {candidate_to_office_link_update_count}, '
        'candidate_ultimate_update_count: {candidate_ultimate_update_count}, '
        'candidate_year_update_count: {candidate_year_update_count}, '
        'contest_measure_update_count: {contest_measure_update_count}, '
        'friends_position_year_candidate_update_count: {friends_position_year_candidate_update_count}, '
        'friends_position_year_measure_update_count: {friends_position_year_measure_update_count}, '
        'friends_ultimate_candidate_update_count: {friends_ultimate_candidate_update_count}, '
        'friends_ultimate_measure_update_count: {friends_ultimate_measure_update_count}, '
        'measure_ultimate_update_count: {measure_ultimate_update_count}, '
        'measure_year_update_count: {measure_year_update_count}, '
        'public_position_year_candidate_update_count: {public_position_year_candidate_update_count}, '
        'public_position_year_measure_update_count: {public_position_year_measure_update_count}, '
        'public_ultimate_candidate_update_count: {public_ultimate_candidate_update_count}, '
        'public_ultimate_measure_update_count: {public_ultimate_measure_update_count}, '
        'status: {status}'
        ''.format(
            candidate_to_office_link_update_count=results['candidate_to_office_link_update_count'],
            candidate_ultimate_update_count=results['candidate_ultimate_update_count'],
            candidate_year_update_count=results['candidate_year_update_count'],
            contest_measure_update_count=results['contest_measure_update_count'],
            friends_position_year_candidate_update_count=results['friends_position_year_candidate_update_count'],
            friends_position_year_measure_update_count=results['friends_position_year_measure_update_count'],
            friends_ultimate_candidate_update_count=results['friends_ultimate_candidate_update_count'],
            friends_ultimate_measure_update_count=results['friends_ultimate_measure_update_count'],
            measure_ultimate_update_count=results['measure_ultimate_update_count'],
            measure_year_update_count=results['measure_year_update_count'],
            public_position_year_candidate_update_count=results['public_position_year_candidate_update_count'],
            public_position_year_measure_update_count=results['public_position_year_measure_update_count'],
            public_ultimate_candidate_update_count=results['public_ultimate_candidate_update_count'],
            public_ultimate_measure_update_count=results['public_ultimate_measure_update_count'],
            status=results['status']))

    # September 2020: Dale commenting this out temporarily. It needs a testing run through, specifically around
    #  how we are treating google_civic_election_id for positions about candidates.
    # results = refresh_cached_position_info_for_election(
    #     google_civic_election_id=google_civic_election_id,
    #     state_code=state_code)
    # public_positions_updated = results['public_positions_updated']
    # friends_only_positions_updated = results['friends_only_positions_updated']
    #
    # messages.add_message(request, messages.INFO,
    #                      'public_positions_updated: {public_positions_updated}, '
    #                      'friends_only_positions_updated: {friends_only_positions_updated}'
    #                      ''.format(public_positions_updated=public_positions_updated,
    #                                friends_only_positions_updated=friends_only_positions_updated))
    return HttpResponseRedirect(reverse('position:position_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code))


@login_required
def refresh_positions_with_candidate_details_for_election_view(request):
    """
    Refresh Positions with candidate details
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = refresh_positions_with_candidate_details_for_election(google_civic_election_id=google_civic_election_id,
                                                                    state_code=state_code)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        positions_updated_count = results['positions_updated_count']
        messages.add_message(request, messages.INFO,
                             "Social media retrieved. Positions refreshed: {update_all_positions_results_count},"
                             .format(update_all_positions_results_count=positions_updated_count))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code))


@login_required
def refresh_positions_with_contest_office_details_for_election_view(request):
    """
    Refresh positions with contest office details
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    contest_office_id = request.GET.get('office_id', 0)
    contest_office_we_vote_id = request.GET.get('office_we_vote_id', '')

    if positive_value_exists(contest_office_id):
        results = push_contest_office_data_to_other_table_caches(contest_office_id)
    elif positive_value_exists(contest_office_we_vote_id):
        results = push_contest_office_data_to_other_table_caches(contest_office_we_vote_id)
    elif positive_value_exists(google_civic_election_id):
        results = refresh_positions_with_contest_office_details_for_election(
            google_civic_election_id=google_civic_election_id, state_code=state_code)
    else:
        results = refresh_positions_with_contest_office_details_for_election(
            google_civic_election_id=google_civic_election_id, state_code=state_code)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        positions_updated_count = results['positions_updated_count']
        messages.add_message(request, messages.INFO,
                             "Social media retrieved. Positions refreshed: {update_all_positions_results_count},"
                             .format(update_all_positions_results_count=positions_updated_count))

    if positive_value_exists(google_civic_election_id):
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code))
    elif positive_value_exists(contest_office_id):
        return HttpResponseRedirect(reverse('office:office_summary', args=(contest_office_id,)))
    else:
        return HttpResponseRedirect (reverse ('office:office_list', args=()) +
                                     '?google_civic_election_id=' + str (google_civic_election_id) +
                                     '&state_code=' + str (state_code))


@login_required
def refresh_positions_with_contest_measure_details_for_election_view(request):
    """
    Refresh positions with contest measure details
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    contest_measure_id = request.GET.get('measure_id', 0)
    contest_measure_we_vote_id = request.GET.get('measure_we_vote_id', '')

    if positive_value_exists(contest_measure_id):
        results = push_contest_measure_data_to_other_table_caches(contest_measure_id)
    elif positive_value_exists(contest_measure_we_vote_id):
        results = push_contest_measure_data_to_other_table_caches(contest_measure_we_vote_id)
    elif positive_value_exists(google_civic_election_id):
        results = refresh_positions_with_contest_measure_details_for_election(
            google_civic_election_id=google_civic_election_id, state_code=state_code)
    else:
        results = refresh_positions_with_contest_measure_details_for_election(
            google_civic_election_id=google_civic_election_id, state_code=state_code)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        positions_updated_count = results['positions_updated_count']
        messages.add_message(request, messages.INFO,
                             "Social media retrieved. Positions refreshed: {update_all_positions_results_count},"
                             .format(update_all_positions_results_count=positions_updated_count))

    if positive_value_exists(google_civic_election_id):
        return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code))
    elif positive_value_exists(contest_measure_id):
        return HttpResponseRedirect(reverse('measure:measure_summary', args=(contest_measure_id,)))
    else:
        return HttpResponseRedirect (reverse ('measure:measure_list', args=()) +
                                     '?google_civic_election_id=' + str (google_civic_election_id) +
                                     '&state_code=' + str (state_code))


@login_required
def relink_candidates_measures_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages.add_message(request, messages.INFO, 'TO BE BUILT: relink_candidates_measures_view')
    return HttpResponseRedirect(reverse('position:position_list', args=()))


@login_required
def position_delete_process_view(request):
    """
    Delete a position
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    position_we_vote_id = request.GET.get('position_we_vote_id', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    # Retrieve this position
    position_on_stage_found = False
    position_on_stage = PositionEntered()
    organization_id = 0
    try:
        position_query = PositionEntered.objects.filter(we_vote_id=position_we_vote_id)
        if len(position_query):
            position_on_stage = position_query[0]
            organization_id = position_on_stage.organization_id
            position_on_stage_found = True
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not find position -- exception.')

    if not position_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find position.')
        return HttpResponseRedirect(reverse('position:position_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    try:
        if position_on_stage_found:
            # Delete
            position_on_stage.delete()
            messages.add_message(request, messages.INFO, 'Position deleted.')
            if positive_value_exists(organization_id):
                return HttpResponseRedirect(reverse('organization:organization_position_list',
                                                    args=([organization_id])) +
                                            "?google_civic_election_id=" + str(google_civic_election_id))
        else:
            messages.add_message(request, messages.ERROR, 'Could not find position.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save position.')

    return HttpResponseRedirect(reverse('position:position_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))
