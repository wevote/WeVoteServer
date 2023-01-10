# representative/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.controllers import retrieve_candidate_photos
from candidate.models import CandidateManager
from office_held.models import OfficeHeld
from exception.models import handle_record_not_found_exception, handle_record_found_more_than_one_exception, \
    print_to_log, handle_record_not_saved_exception
from import_export_vote_smart.models import VoteSmartRatingOneCandidate
from import_export_vote_smart.votesmart_local import VotesmartApiError
from .models import Representative
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from django.db.models import Q
from election.models import Election
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP, \
    extract_twitter_handle_from_text_string, convert_to_political_party_constant

OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def representative_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    representative_search = request.GET.get('representative_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all = request.GET.get('show_all', False)
    representative_list = []

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        representative_list = Representative.objects.all()
        if positive_value_exists(state_code):
            representative_list = representative_list.filter(state_code__iexact=state_code)

        if positive_value_exists(representative_search):
            search_words = representative_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(representative_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(representative_twitter_handle__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(political_party__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    representative_list = representative_list.filter(final_filters)

        if not positive_value_exists(show_all):
            representative_list = representative_list.order_by('representative_name')[:25]
    except ObjectDoesNotExist:
        # This is fine
        pass

    # Cycle through all Representatives and find unlinked Candidates that *might* be "children" of this
    # representative
    temp_representative_list = []
    for one_representative in representative_list:
        try:
            filters = []
            if positive_value_exists(one_representative.representative_twitter_handle):
                new_filter = (
                    Q(candidate_twitter_handle__iexact=one_representative.representative_twitter_handle) |
                    Q(candidate_twitter_handle2__iexact=one_representative.representative_twitter_handle) |
                    Q(candidate_twitter_handle3__iexact=one_representative.representative_twitter_handle)
                )
                filters.append(new_filter)

            if positive_value_exists(one_representative.vote_smart_id):
                new_filter = Q(vote_smart_id=one_representative.vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

        except Exception as e:
            related_candidate_list_count = 0

        temp_representative_list.append(one_representative)

    representative_list = temp_representative_list

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'representative_list':    representative_list,
        'representative_search':  representative_search,
        'election_list':            election_list,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'representative/representative_list.html', template_values)


@login_required
def representative_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    office_held_id = request.GET.get('office_held_id', 0)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    representative_name = request.GET.get('representative_name', "")
    google_civic_representative_name = request.GET.get('google_civic_representative_name', "")
    state_code = request.GET.get('state_code', "")
    representative_twitter_handle = request.GET.get('representative_twitter_handle', "")
    representative_url = request.GET.get('representative_url', "")
    political_party = request.GET.get('political_party', "")
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', "")
    vote_smart_id = request.GET.get('vote_smart_id', "")
    maplight_id = request.GET.get('maplight_id', "")
    representative_we_vote_id = request.GET.get('representative_we_vote_id', "")

    # These are the Offices Held already entered for this election
    try:
        office_held_list = OfficeHeld.objects.order_by('office_held_name')
        office_held_list = office_held_list.filter(google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        office_held_list = []

    # Its helpful to see existing representatives when entering a new representative
    representative_list = []
    try:
        representative_list = Representative.objects.all()
        if positive_value_exists(google_civic_election_id):
            representative_list = representative_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(office_held_id):
            representative_list = representative_list.filter(office_held_id=office_held_id)
        representative_list = representative_list.order_by('representative_name')[:500]
    except Representative.DoesNotExist:
        # This is fine, create new
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'office_held_list':                  office_held_list,
        # We need to always pass in separately for the template to work
        'office_held_id':                    office_held_id,
        'google_civic_election_id':             google_civic_election_id,
        'representative_list':                representative_list,
        # Incoming variables, not saved yet
        'representative_name':                representative_name,
        'google_civic_representative_name':   google_civic_representative_name,
        'state_code':                           state_code,
        'representative_twitter_handle':      representative_twitter_handle,
        'representative_url':                 representative_url,
        'political_party':                      political_party,
        'ballot_guide_official_statement':      ballot_guide_official_statement,
        'vote_smart_id':                        vote_smart_id,
        'maplight_id':                          maplight_id,
        'representative_we_vote_id':          representative_we_vote_id,
    }
    return render(request, 'representative/representative_edit.html', template_values)


@login_required
def representative_edit_view(request, representative_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    representative_name = request.GET.get('representative_name', False)
    state_code = request.GET.get('state_code', False)
    google_civic_representative_name = request.GET.get('google_civic_representative_name', False)
    representative_twitter_handle = request.GET.get('representative_twitter_handle', False)
    representative_url = request.GET.get('representative_url', False)
    political_party = request.GET.get('political_party', False)
    vote_smart_id = request.GET.get('vote_smart_id', False)
    maplight_id = request.GET.get('maplight_id', False)

    messages_on_stage = get_messages(request)
    representative_id = convert_to_int(representative_id)
    representative_on_stage_found = False
    representative_on_stage = Representative()
    duplicate_representative_list = []

    try:
        representative_on_stage = Representative.objects.get(id=representative_id)
        representative_on_stage_found = True
    except Representative.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Representative.DoesNotExist:
        # This is fine, create new below
        pass

    if representative_on_stage_found:
        try:
            vote_smart_representative_id = representative_on_stage.vote_smart_id
            rating_list_query = VoteSmartRatingOneCandidate.objects.order_by('-timeSpan')  # Desc order
            rating_list = rating_list_query.filter(candidateId=vote_smart_representative_id)
        except VotesmartApiError as error_instance:
            # Catch the error message coming back from Vote Smart and pass it in the status
            error_message = error_instance.args
            status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
            print_to_log(logger=logger, exception_message_optional=status)
            rating_list = []

        # Find possible duplicate representatives
        try:
            duplicate_representative_list = Representative.objects.all()
            duplicate_representative_list = duplicate_representative_list.exclude(
                we_vote_id__iexact=representative_on_stage.we_vote_id)

            filters = []
            new_filter = Q(representative_name__icontains=representative_on_stage.representative_name)
            filters.append(new_filter)

            if positive_value_exists(representative_on_stage.representative_twitter_handle):
                new_filter = Q(representative_twitter_handle__icontains=representative_on_stage.representative_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(representative_on_stage.vote_smart_id):
                new_filter = Q(vote_smart_id=representative_on_stage.vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                duplicate_representative_list = duplicate_representative_list.filter(final_filters)

            duplicate_representative_list = duplicate_representative_list.order_by('representative_name')[:20]
        except ObjectDoesNotExist:
            # This is fine, create new
            pass

        template_values = {
            'messages_on_stage':                    messages_on_stage,
            'representative':                     representative_on_stage,
            'rating_list':                          rating_list,
            'duplicate_representative_list':      duplicate_representative_list,
            # Incoming variables, not saved yet
            'representative_name':                representative_name,
            'state_code':                           state_code,
            'google_civic_representative_name':   google_civic_representative_name,
            'representative_twitter_handle':      representative_twitter_handle,
            'representative_url':                 representative_url,
            'political_party':                      political_party,
            'vote_smart_id':                        vote_smart_id,
            'maplight_id':                          maplight_id,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            # Incoming variables
            'vote_smart_id':      vote_smart_id,
        }
    return render(request, 'representative/representative_edit.html', template_values)


@login_required
def representative_edit_process_view(request):
    """
    Process the new or edit representative forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    representative_id = convert_to_int(request.POST['representative_id'])
    representative_name = request.POST.get('representative_name', False)
    google_civic_representative_name = request.POST.get('google_civic_representative_name', False)
    representative_twitter_handle = request.POST.get('representative_twitter_handle', False)
    if positive_value_exists(representative_twitter_handle):
        representative_twitter_handle = extract_twitter_handle_from_text_string(representative_twitter_handle)
    representative_url = request.POST.get('representative_url', False)
    political_party = request.POST.get('political_party', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    maplight_id = request.POST.get('maplight_id', False)
    state_code = request.POST.get('state_code', False)
    representative_we_vote_id = request.POST.get('representative_we_vote_id', False)

    # Check to see if this representative is already being used anywhere
    representative_on_stage_found = False
    representative_on_stage = Representative()
    if positive_value_exists(representative_id):
        try:
            representative_query = Representative.objects.filter(id=representative_id)
            if len(representative_query):
                representative_on_stage = representative_query[0]
                representative_on_stage_found = True
        except Exception as e:
            pass

    # Check to see if there is a duplicate representative already saved for this election
    existing_representative_found = False
    if not positive_value_exists(representative_id):
        try:
            filter_list = Q()

            at_least_one_filter = False
            if positive_value_exists(vote_smart_id):
                at_least_one_filter = True
                filter_list |= Q(vote_smart_id=vote_smart_id)
            if positive_value_exists(maplight_id):
                at_least_one_filter = True
                filter_list |= Q(maplight_id=maplight_id)
            if positive_value_exists(representative_twitter_handle):
                at_least_one_filter = True
                filter_list |= Q(representative_twitter_handle=representative_twitter_handle)

            if at_least_one_filter:
                representative_duplicates_query = Representative.objects.filter(filter_list)

                if len(representative_duplicates_query):
                    existing_representative_found = True
        except Exception as e:
            pass

    try:
        if existing_representative_found:
            messages.add_message(request, messages.ERROR, 'This representative is already saved for this election.')
            url_variables = "?representative_name=" + str(representative_name) + \
                            "&state_code=" + str(state_code) + \
                            "&google_civic_representative_name=" + str(google_civic_representative_name) + \
                            "&representative_twitter_handle=" + str(representative_twitter_handle) + \
                            "&representative_url=" + str(representative_url) + \
                            "&political_party=" + str(political_party) + \
                            "&vote_smart_id=" + str(vote_smart_id) + \
                            "&representative_we_vote_id=" + str(representative_we_vote_id) + \
                            "&maplight_id=" + str(maplight_id)
            return HttpResponseRedirect(reverse('representative:representative_new', args=()) + url_variables)
        elif representative_on_stage_found:
            # Update
            if representative_name is not False:
                representative_on_stage.representative_name = representative_name
            if state_code is not False:
                representative_on_stage.state_code = state_code
            if google_civic_representative_name is not False:
                representative_on_stage.google_civic_representative_name = google_civic_representative_name
            if representative_twitter_handle is not False:
                representative_on_stage.representative_twitter_handle = representative_twitter_handle
            if representative_url is not False:
                representative_on_stage.representative_url = representative_url
            if political_party is not False:
                political_party = convert_to_political_party_constant(political_party)
                representative_on_stage.political_party = political_party
            if vote_smart_id is not False:
                representative_on_stage.vote_smart_id = vote_smart_id
            if maplight_id is not False:
                representative_on_stage.maplight_id = maplight_id

            representative_on_stage.save()
            messages.add_message(request, messages.INFO, 'Representative updated.')
        else:
            # Create new

            required_representative_variables = True \
                if positive_value_exists(representative_name) \
                else False
            if required_representative_variables:
                representative_on_stage = Representative(
                    representative_name=representative_name,
                    state_code=state_code,
                )
                if google_civic_representative_name is not False:
                    representative_on_stage.google_civic_representative_name = google_civic_representative_name
                if representative_twitter_handle is not False:
                    representative_on_stage.representative_twitter_handle = representative_twitter_handle
                if representative_url is not False:
                    representative_on_stage.representative_url = representative_url
                if political_party is not False:
                    political_party = convert_to_political_party_constant(political_party)
                    representative_on_stage.political_party = political_party
                if vote_smart_id is not False:
                    representative_on_stage.vote_smart_id = vote_smart_id
                if maplight_id is not False:
                    representative_on_stage.maplight_id = maplight_id
                if representative_we_vote_id is not False:
                    representative_on_stage.we_vote_id = representative_we_vote_id

                representative_on_stage.save()
                representative_id = representative_on_stage.id
                messages.add_message(request, messages.INFO, 'New representative saved.')
            else:
                # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
                url_variables = "?representative_name=" + str(representative_name) + \
                                "&state_code=" + str(state_code) + \
                                "&google_civic_representative_name=" + str(google_civic_representative_name) + \
                                "&representative_twitter_handle=" + str(representative_twitter_handle) + \
                                "&representative_url=" + str(representative_url) + \
                                "&political_party=" + str(political_party) + \
                                "&vote_smart_id=" + str(vote_smart_id) + \
                                "&representative_we_vote_id=" + str(representative_we_vote_id) + \
                                "&maplight_id=" + str(maplight_id)
                if positive_value_exists(representative_id):
                    return HttpResponseRedirect(reverse('representative:representative_edit',
                                                        args=(representative_id,)) + url_variables)
                else:
                    return HttpResponseRedirect(reverse('representative:representative_new', args=()) +
                                                url_variables)

    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save representative.')
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))

    if representative_id:
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))
    else:
        return HttpResponseRedirect(reverse('representative:representative_new', args=()))


@login_required
def representative_retrieve_photos_view(request, candidate_id):  # TODO DALE Transition fully to representative
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
def representative_delete_process_view(request):  # TODO DALE Transition fully to representative
    """
    Delete this representative
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    representative_id = convert_to_int(request.GET.get('representative_id', 0))

    # Retrieve this representative
    representative_on_stage_found = False
    representative_on_stage = Representative()
    if positive_value_exists(representative_id):
        try:
            representative_query = Representative.objects.filter(id=representative_id)
            if len(representative_query):
                representative_on_stage = representative_query[0]
                representative_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find representative -- exception.')

    if not representative_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find representative.')
        return HttpResponseRedirect(reverse('representative:representative_list', args=()))

    try:
        # Delete the representative
        representative_on_stage.delete()
        messages.add_message(request, messages.INFO, 'Representative deleted.')
        return HttpResponseRedirect(reverse('representative:representative_list', args=()))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete representative -- exception.')
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))
