# politician/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import politicians_import_from_master_server
from .models import Politician, PoliticianManager
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaign
from config.base import get_environment_variable
from office.models import ContestOffice, ContestOfficeManager
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponse
import json
from django.shortcuts import render
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception, print_to_log
from import_export_vote_smart.models import VoteSmartRatingOneCandidate
from import_export_vote_smart.votesmart_local import VotesmartApiError
from position.models import PositionEntered, PositionListManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, convert_to_political_party_constant, \
    extract_first_name_from_full_name, \
    extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, extract_twitter_handle_from_text_string, \
    positive_value_exists, STATE_CODE_MAP

POLITICIANS_SYNC_URL = get_environment_variable("POLITICIANS_SYNC_URL")  # politiciansSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


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
    authority_required = {'partner_organization', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    politician_search = request.GET.get('politician_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all = request.GET.get('show_all', False)
    politician_list = []

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        politician_list = Politician.objects.all()
        if positive_value_exists(state_code):
            politician_list = politician_list.filter(state_code__iexact=state_code)

        if positive_value_exists(politician_search):
            search_words = politician_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(politician_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(politician_twitter_handle__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(political_party__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    politician_list = politician_list.filter(final_filters)

        if not positive_value_exists(show_all):
            politician_list = politician_list.order_by('politician_name')[:25]
    except ObjectDoesNotExist:
        # This is fine
        pass

    # Cycle through all Politicians and find unlinked Candidates that *might* be "children" of this politician
    temp_politician_list = []
    for one_politician in politician_list:
        try:
            linked_candidate_query = CandidateCampaign.objects.all()
            linked_candidate_query = linked_candidate_query.filter(politician_we_vote_id=one_politician.we_vote_id)
            linked_candidate_list_count = linked_candidate_query.count()
            one_politician.linked_candidate_list_count = linked_candidate_list_count

            related_candidate_list = CandidateCampaign.objects.all()
            related_candidate_list = related_candidate_list.exclude(politician_we_vote_id=one_politician.we_vote_id)

            filters = []
            new_filter = Q(candidate_name__icontains=one_politician.first_name) & \
                Q(candidate_name__icontains=one_politician.last_name)
            filters.append(new_filter)

            if positive_value_exists(one_politician.politician_twitter_handle):
                new_filter = Q(candidate_twitter_handle__iexact=one_politician.politician_twitter_handle)
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

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'politician_list':          politician_list,
        'politician_search':        politician_search,
        'election_list':            election_list,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'politician/politician_list.html', template_values)


@login_required
def politician_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    contest_office_id = request.GET.get('contest_office_id', 0)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    politician_name = request.GET.get('politician_name', "")
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', "")
    state_code = request.GET.get('state_code', "")
    politician_twitter_handle = request.GET.get('politician_twitter_handle', "")
    politician_url = request.GET.get('politician_url', "")
    political_party = request.GET.get('political_party', "")
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', "")
    vote_smart_id = request.GET.get('vote_smart_id', "")
    maplight_id = request.GET.get('maplight_id', "")
    politician_we_vote_id = request.GET.get('politician_we_vote_id', "")

    # These are the Offices already entered for this election
    try:
        contest_office_list = ContestOffice.objects.order_by('office_name')
        contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        contest_office_list = []

    # Its helpful to see existing politicians when entering a new politician
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
        'messages_on_stage':        messages_on_stage,
        'office_list':              contest_office_list,
        'contest_office_id':        contest_office_id,  # We need to always pass in separately for the template to work
        'google_civic_election_id': google_civic_election_id,
        'politician_list':           politician_list,
        # Incoming variables, not saved yet
        'politician_name':                   politician_name,
        'google_civic_candidate_name':      google_civic_candidate_name,
        'state_code':                       state_code,
        'politician_twitter_handle':         politician_twitter_handle,
        'politician_url':                    politician_url,
        'political_party':                            political_party,
        'ballot_guide_official_statement':  ballot_guide_official_statement,
        'vote_smart_id':                    vote_smart_id,
        'maplight_id':                      maplight_id,
        'politician_we_vote_id':            politician_we_vote_id,
    }
    return render(request, 'politician/politician_edit.html', template_values)


@login_required
def politician_edit_by_we_vote_id_view(request, politician_we_vote_id):
    politician_manager = PoliticianManager()
    politician_id = politician_manager.fetch_politician_id_from_we_vote_id(politician_we_vote_id)
    return politician_we_vote_id(request, politician_id)


@login_required
def politician_edit_view(request, politician_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    politician_name = request.GET.get('politician_name', False)
    state_code = request.GET.get('state_code', False)
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', False)
    politician_twitter_handle = request.GET.get('politician_twitter_handle', False)
    politician_url = request.GET.get('politician_url', False)
    political_party = request.GET.get('political_party', False)
    vote_smart_id = request.GET.get('vote_smart_id', False)
    maplight_id = request.GET.get('maplight_id', False)

    messages_on_stage = get_messages(request)
    politician_id = convert_to_int(politician_id)
    politician_on_stage_found = False
    politician_on_stage = Politician()
    duplicate_politician_list = []

    try:
        politician_on_stage = Politician.objects.get(id=politician_id)
        politician_on_stage_found = True
    except Politician.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Politician.DoesNotExist:
        # This is fine, create new below
        pass

    if politician_on_stage_found:
        # Working with Vote Smart data
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

        # Working with We Vote Positions
        try:
            politician_position_query = PositionEntered.objects.order_by('stance')
            # As of Aug 2018 we are no longer using PERCENT_RATING
            politician_position_query = politician_position_query.exclude(stance__iexact='PERCENT_RATING')
            politician_position_list = politician_position_query.filter(
                politician_we_vote_id__iexact=politician_on_stage.we_vote_id)
        except Exception as e:
            politician_position_list = []

        # Working with Candidate "children" of this politician
        try:
            linked_candidate_list = CandidateCampaign.objects.all()
            linked_candidate_list = linked_candidate_list.filter(
                politician_we_vote_id__iexact=politician_on_stage.we_vote_id)
        except Exception as e:
            linked_candidate_list = []

        # Finding Candidates that *might* be "children" of this politician
        try:
            related_candidate_list = CandidateCampaign.objects.all()
            related_candidate_list = related_candidate_list.exclude(
                politician_we_vote_id__iexact=politician_on_stage.we_vote_id)

            filters = []
            new_filter = Q(candidate_name__icontains=politician_on_stage.first_name) & \
                Q(candidate_name__icontains=politician_on_stage.last_name)
            filters.append(new_filter)

            if positive_value_exists(politician_on_stage.politician_twitter_handle):
                new_filter = Q(candidate_twitter_handle__iexact=politician_on_stage.politician_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(politician_on_stage.vote_smart_id):
                new_filter = Q(vote_smart_id=politician_on_stage.vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                related_candidate_list = related_candidate_list.filter(final_filters)

            related_candidate_list = related_candidate_list.order_by('candidate_name')[:20]
        except Exception as e:
            related_candidate_list = []

        # Find possible duplicate politicians
        try:
            duplicate_politician_list = Politician.objects.all()
            duplicate_politician_list = duplicate_politician_list.exclude(
                we_vote_id__iexact=politician_on_stage.we_vote_id)

            filters = []
            new_filter = Q(politician_name__icontains=politician_on_stage.politician_name)
            filters.append(new_filter)

            if positive_value_exists(politician_on_stage.first_name) or \
                    positive_value_exists(politician_on_stage.last_name):
                new_filter = Q(first_name__icontains=politician_on_stage.first_name) & \
                    Q(last_name__icontains=politician_on_stage.last_name)
                filters.append(new_filter)

            if positive_value_exists(politician_on_stage.politician_twitter_handle):
                new_filter = Q(politician_twitter_handle__icontains=politician_on_stage.politician_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(politician_on_stage.vote_smart_id):
                new_filter = Q(vote_smart_id=politician_on_stage.vote_smart_id)
                filters.append(new_filter)

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

        template_values = {
            'messages_on_stage':            messages_on_stage,
            'politician':                   politician_on_stage,
            'rating_list':                  rating_list,
            'politician_position_list':     politician_position_list,
            'linked_candidate_list':        linked_candidate_list,
            'related_candidate_list':       related_candidate_list,
            'duplicate_politician_list':    duplicate_politician_list,
            # Incoming variables, not saved yet
            'politician_name':              politician_name,
            'state_code':                   state_code,
            'google_civic_candidate_name':  google_civic_candidate_name,
            'politician_twitter_handle':    politician_twitter_handle,
            'politician_url':               politician_url,
            'political_party':              political_party,
            'vote_smart_id':                vote_smart_id,
            'maplight_id':                  maplight_id,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            # Incoming variables
            'vote_smart_id':        vote_smart_id,
        }
    return render(request, 'politician/politician_edit.html', template_values)


@login_required
def politician_edit_process_view(request):
    """
    Process the new or edit politician forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician_id = convert_to_int(request.POST['politician_id'])
    politician_name = request.POST.get('politician_name', False)
    google_civic_candidate_name = request.POST.get('google_civic_candidate_name', False)
    politician_twitter_handle = request.POST.get('politician_twitter_handle', False)
    if positive_value_exists(politician_twitter_handle):
        politician_twitter_handle = extract_twitter_handle_from_text_string(politician_twitter_handle)
    politician_url = request.POST.get('politician_url', False)
    political_party = request.POST.get('political_party', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    maplight_id = request.POST.get('maplight_id', False)
    state_code = request.POST.get('state_code', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)

    # Check to see if this politician is already being used anywhere
    politician_on_stage_found = False
    politician_on_stage = Politician()
    if positive_value_exists(politician_id):
        try:
            politician_query = Politician.objects.filter(id=politician_id)
            if len(politician_query):
                politician_on_stage = politician_query[0]
                politician_on_stage_found = True
        except Exception as e:
            pass

    # Check to see if there is a duplicate politician already saved for this election
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
                filter_list |= Q(politician_twitter_handle=politician_twitter_handle)

            if at_least_one_filter:
                politician_duplicates_query = Politician.objects.filter(filter_list)

                if len(politician_duplicates_query):
                    existing_politician_found = True
        except Exception as e:
            pass

    try:
        if existing_politician_found:
            messages.add_message(request, messages.ERROR, 'This politician is already saved for this election.')
            url_variables = "?politician_name=" + str(politician_name) + \
                            "&state_code=" + str(state_code) + \
                            "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                            "&politician_twitter_handle=" + str(politician_twitter_handle) + \
                            "&politician_url=" + str(politician_url) + \
                            "&political_party=" + str(political_party) + \
                            "&vote_smart_id=" + str(vote_smart_id) + \
                            "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                            "&maplight_id=" + str(maplight_id)
            return HttpResponseRedirect(reverse('politician:politician_new', args=()) + url_variables)
        elif politician_on_stage_found:
            # Update
            if politician_name is not False:
                politician_on_stage.politician_name = politician_name
                # Re-save first_name, middle name, and last name
                politician_on_stage.first_name = extract_first_name_from_full_name(politician_name)
                politician_on_stage.middle_name = extract_middle_name_from_full_name(politician_name)
                politician_on_stage.last_name = extract_last_name_from_full_name(politician_name)
            if state_code is not False:
                politician_on_stage.state_code = state_code
            if google_civic_candidate_name is not False:
                politician_on_stage.google_civic_candidate_name = google_civic_candidate_name
            if politician_twitter_handle is not False:
                politician_on_stage.politician_twitter_handle = politician_twitter_handle
            if politician_url is not False:
                politician_on_stage.politician_url = politician_url
            if political_party is not False:
                political_party = convert_to_political_party_constant(political_party)
                politician_on_stage.political_party = political_party
            if vote_smart_id is not False:
                politician_on_stage.vote_smart_id = vote_smart_id
            if maplight_id is not False:
                politician_on_stage.maplight_id = maplight_id

            politician_on_stage.save()
            messages.add_message(request, messages.INFO, 'Politician updated.')
        else:
            # Create new

            required_politician_variables = True \
                if positive_value_exists(politician_name) \
                else False
            if required_politician_variables:
                politician_on_stage = Politician(
                    politician_name=politician_name,
                    state_code=state_code,
                )
                politician_on_stage.first_name = extract_first_name_from_full_name(politician_name)
                politician_on_stage.middle_name = extract_middle_name_from_full_name(politician_name)
                politician_on_stage.last_name = extract_last_name_from_full_name(politician_name)
                if google_civic_candidate_name is not False:
                    politician_on_stage.google_civic_candidate_name = google_civic_candidate_name
                if politician_twitter_handle is not False:
                    politician_on_stage.politician_twitter_handle = politician_twitter_handle
                if politician_url is not False:
                    politician_on_stage.politician_url = politician_url
                if political_party is not False:
                    political_party = convert_to_political_party_constant(political_party)
                    politician_on_stage.political_party = political_party
                if vote_smart_id is not False:
                    politician_on_stage.vote_smart_id = vote_smart_id
                if maplight_id is not False:
                    politician_on_stage.maplight_id = maplight_id
                if politician_we_vote_id is not False:
                    politician_on_stage.politician_we_vote_id = politician_we_vote_id

                politician_on_stage.save()
                politician_id = politician_on_stage.id
                messages.add_message(request, messages.INFO, 'New politician saved.')
            else:
                # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
                url_variables = "?politician_name=" + str(politician_name) + \
                                "&state_code=" + str(state_code) + \
                                "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                                "&politician_twitter_handle=" + str(politician_twitter_handle) + \
                                "&politician_url=" + str(politician_url) + \
                                "&political_party=" + str(political_party) + \
                                "&vote_smart_id=" + str(vote_smart_id) + \
                                "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                                "&maplight_id=" + str(maplight_id)
                if positive_value_exists(politician_id):
                    return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)) +
                                                url_variables)
                else:
                    return HttpResponseRedirect(reverse('politician:politician_new', args=()) +
                                                url_variables)

    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save politician.')
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))

    if politician_id:
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))
    else:
        return HttpResponseRedirect(reverse('politician:politician_new', args=()))


@login_required
def politician_retrieve_photos_view(request, candidate_id):  # TODO DALE Transition fully to politician
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(candidate_id)
    force_retrieve = request.GET.get('force_retrieve', 0)

    candidate_campaign_manager = CandidateCampaignManager()

    results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
    if not positive_value_exists(results['candidate_campaign_found']):
        messages.add_message(request, messages.ERROR,
                             "Candidate '{candidate_id}' not found.".format(candidate_id=candidate_id))
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    we_vote_candidate = results['candidate_campaign']

    display_messages = True
    retrieve_candidate_results = retrieve_candidate_photos(we_vote_candidate, force_retrieve)

    if retrieve_candidate_results['status'] and display_messages:
        messages.add_message(request, messages.INFO, retrieve_candidate_results['status'])
    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))


@login_required
def politician_delete_process_view(request):  # TODO DALE Transition fully to politician
    """
    Delete this politician
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician_id = convert_to_int(request.GET.get('politician_id', 0))

    # Retrieve this politician
    politician_on_stage_found = False
    politician_on_stage = Politician()
    if positive_value_exists(politician_id):
        try:
            politician_query = Politician.objects.filter(id=politician_id)
            if len(politician_query):
                politician_on_stage = politician_query[0]
                politician_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find politician -- exception.')

    if not politician_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find politician.')
        return HttpResponseRedirect(reverse('politician:politician_list', args=()))

    # Are there any positions attached to this politician that should be moved to another
    # instance of this politician?
    position_list_manager = PositionListManager()
    retrieve_public_positions = True  # The alternate is positions for friends-only
    position_list = position_list_manager.retrieve_all_positions_for_politician(retrieve_public_positions, politician_id)
    if positive_value_exists(len(position_list)):
        positions_found_for_this_politician = True
    else:
        positions_found_for_this_politician = False

    try:
        if not positions_found_for_this_politician:
            # Delete the politician
            politician_on_stage.delete()
            messages.add_message(request, messages.INFO, 'Candidate Campaign deleted.')
        else:
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'positions still attached to this politician.')
            return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete politician -- exception.')
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))

    return HttpResponseRedirect(reverse('politician:politician_list', args=()))


# This page does not need to be protected.
def politicians_sync_out_view(request):  # politiciansSyncOut
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

            new_filter = Q(politician_url__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(party__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__icontains=politician_search)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                politician_query = politician_query.filter(final_filters)

        politician_query = politician_query.values(
            'we_vote_id', 'first_name', 'middle_name', 'last_name',
            'politician_name', 'google_civic_candidate_name', 'full_name_assembled', 'gender',
            'birth_date', 'bioguide_id', 'thomas_id', 'lis_id', 'govtrack_id',
            'opensecrets_id', 'vote_smart_id', 'fec_id', 'cspan_id',
            'wikipedia_id', 'ballotpedia_id', 'house_history_id',
            'maplight_id', 'washington_post_id', 'icpsr_id',
            'political_party', 'state_code', 'politician_url',
            'politician_twitter_handle',
            'we_vote_hosted_profile_image_url_large', 'we_vote_hosted_profile_image_url_medium',
            'we_vote_hosted_profile_image_url_tiny', 'ctcl_uuid', 'politician_facebook_id',
            'politician_phone_number', 'politician_googleplus_id', 'politician_youtube_id', 'politician_email_address')
        if politician_query:
            politician_list_json = list(politician_query)
            return HttpResponse(json.dumps(politician_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'POLITICIAN_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
