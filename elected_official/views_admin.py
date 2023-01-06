# elected_official/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.controllers import retrieve_candidate_photos
from candidate.models import CandidateManager
from elected_office.models import ElectedOffice
from exception.models import handle_record_not_found_exception, handle_record_found_more_than_one_exception, \
    print_to_log, handle_record_not_saved_exception
from import_export_vote_smart.models import VoteSmartRatingOneCandidate
from import_export_vote_smart.votesmart_local import VotesmartApiError
from .models import ElectedOfficial
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
def elected_official_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    elected_official_search = request.GET.get('elected_official_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all = request.GET.get('show_all', False)
    elected_official_list = []

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        elected_official_list = ElectedOfficial.objects.all()
        if positive_value_exists(state_code):
            elected_official_list = elected_official_list.filter(state_code__iexact=state_code)

        if positive_value_exists(elected_official_search):
            search_words = elected_official_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(elected_official_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(elected_official_twitter_handle__icontains=one_word)
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

                    elected_official_list = elected_official_list.filter(final_filters)

        if not positive_value_exists(show_all):
            elected_official_list = elected_official_list.order_by('elected_official_name')[:25]
    except ObjectDoesNotExist:
        # This is fine
        pass

    # Cycle through all Elected Officials and find unlinked Candidates that *might* be "children" of this
    # elected_official
    temp_elected_official_list = []
    for one_elected_official in elected_official_list:
        try:
            filters = []
            if positive_value_exists(one_elected_official.elected_official_twitter_handle):
                new_filter = (
                    Q(candidate_twitter_handle__iexact=one_elected_official.elected_official_twitter_handle) |
                    Q(candidate_twitter_handle2__iexact=one_elected_official.elected_official_twitter_handle) |
                    Q(candidate_twitter_handle3__iexact=one_elected_official.elected_official_twitter_handle)
                )
                filters.append(new_filter)

            if positive_value_exists(one_elected_official.vote_smart_id):
                new_filter = Q(vote_smart_id=one_elected_official.vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

        except Exception as e:
            related_candidate_list_count = 0

        temp_elected_official_list.append(one_elected_official)

    elected_official_list = temp_elected_official_list

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'elected_official_list':    elected_official_list,
        'elected_official_search':  elected_official_search,
        'election_list':            election_list,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'elected_official/elected_official_list.html', template_values)


@login_required
def elected_official_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    elected_office_id = request.GET.get('elected_office_id', 0)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    elected_official_name = request.GET.get('elected_official_name', "")
    google_civic_elected_official_name = request.GET.get('google_civic_elected_official_name', "")
    state_code = request.GET.get('state_code', "")
    elected_official_twitter_handle = request.GET.get('elected_official_twitter_handle', "")
    elected_official_url = request.GET.get('elected_official_url', "")
    political_party = request.GET.get('political_party', "")
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', "")
    vote_smart_id = request.GET.get('vote_smart_id', "")
    maplight_id = request.GET.get('maplight_id', "")
    elected_official_we_vote_id = request.GET.get('elected_official_we_vote_id', "")

    # These are the Elected Offices already entered for this election
    try:
        elected_office_list = ElectedOffice.objects.order_by('elected_office_name')
        elected_office_list = elected_office_list.filter(google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        elected_office_list = []

    # Its helpful to see existing elected_officials when entering a new elected_official
    elected_official_list = []
    try:
        elected_official_list = ElectedOfficial.objects.all()
        if positive_value_exists(google_civic_election_id):
            elected_official_list = elected_official_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(elected_office_id):
            elected_official_list = elected_official_list.filter(elected_office_id=elected_office_id)
        elected_official_list = elected_official_list.order_by('elected_official_name')[:500]
    except ElectedOfficial.DoesNotExist:
        # This is fine, create new
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'elected_office_list':                  elected_office_list,
        # We need to always pass in separately for the template to work
        'elected_office_id':                    elected_office_id,
        'google_civic_election_id':             google_civic_election_id,
        'elected_official_list':                elected_official_list,
        # Incoming variables, not saved yet
        'elected_official_name':                elected_official_name,
        'google_civic_elected_official_name':   google_civic_elected_official_name,
        'state_code':                           state_code,
        'elected_official_twitter_handle':      elected_official_twitter_handle,
        'elected_official_url':                 elected_official_url,
        'political_party':                      political_party,
        'ballot_guide_official_statement':      ballot_guide_official_statement,
        'vote_smart_id':                        vote_smart_id,
        'maplight_id':                          maplight_id,
        'elected_official_we_vote_id':          elected_official_we_vote_id,
    }
    return render(request, 'elected_official/elected_official_edit.html', template_values)


@login_required
def elected_official_edit_view(request, elected_official_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    elected_official_name = request.GET.get('elected_official_name', False)
    state_code = request.GET.get('state_code', False)
    google_civic_elected_official_name = request.GET.get('google_civic_elected_official_name', False)
    elected_official_twitter_handle = request.GET.get('elected_official_twitter_handle', False)
    elected_official_url = request.GET.get('elected_official_url', False)
    political_party = request.GET.get('political_party', False)
    vote_smart_id = request.GET.get('vote_smart_id', False)
    maplight_id = request.GET.get('maplight_id', False)

    messages_on_stage = get_messages(request)
    elected_official_id = convert_to_int(elected_official_id)
    elected_official_on_stage_found = False
    elected_official_on_stage = ElectedOfficial()
    duplicate_elected_official_list = []

    try:
        elected_official_on_stage = ElectedOfficial.objects.get(id=elected_official_id)
        elected_official_on_stage_found = True
    except ElectedOfficial.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ElectedOfficial.DoesNotExist:
        # This is fine, create new below
        pass

    if elected_official_on_stage_found:
        try:
            vote_smart_elected_official_id = elected_official_on_stage.vote_smart_id
            rating_list_query = VoteSmartRatingOneCandidate.objects.order_by('-timeSpan')  # Desc order
            rating_list = rating_list_query.filter(candidateId=vote_smart_elected_official_id)
        except VotesmartApiError as error_instance:
            # Catch the error message coming back from Vote Smart and pass it in the status
            error_message = error_instance.args
            status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
            print_to_log(logger=logger, exception_message_optional=status)
            rating_list = []

        # Find possible duplicate elected_officials
        try:
            duplicate_elected_official_list = ElectedOfficial.objects.all()
            duplicate_elected_official_list = duplicate_elected_official_list.exclude(
                we_vote_id__iexact=elected_official_on_stage.we_vote_id)

            filters = []
            new_filter = Q(elected_official_name__icontains=elected_official_on_stage.elected_official_name)
            filters.append(new_filter)

            if positive_value_exists(elected_official_on_stage.elected_official_twitter_handle):
                new_filter = Q(elected_official_twitter_handle__icontains=elected_official_on_stage.elected_official_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(elected_official_on_stage.vote_smart_id):
                new_filter = Q(vote_smart_id=elected_official_on_stage.vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                duplicate_elected_official_list = duplicate_elected_official_list.filter(final_filters)

            duplicate_elected_official_list = duplicate_elected_official_list.order_by('elected_official_name')[:20]
        except ObjectDoesNotExist:
            # This is fine, create new
            pass

        template_values = {
            'messages_on_stage':                    messages_on_stage,
            'elected_official':                     elected_official_on_stage,
            'rating_list':                          rating_list,
            'duplicate_elected_official_list':      duplicate_elected_official_list,
            # Incoming variables, not saved yet
            'elected_official_name':                elected_official_name,
            'state_code':                           state_code,
            'google_civic_elected_official_name':   google_civic_elected_official_name,
            'elected_official_twitter_handle':      elected_official_twitter_handle,
            'elected_official_url':                 elected_official_url,
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
    return render(request, 'elected_official/elected_official_edit.html', template_values)


@login_required
def elected_official_edit_process_view(request):
    """
    Process the new or edit elected_official forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    elected_official_id = convert_to_int(request.POST['elected_official_id'])
    elected_official_name = request.POST.get('elected_official_name', False)
    google_civic_elected_official_name = request.POST.get('google_civic_elected_official_name', False)
    elected_official_twitter_handle = request.POST.get('elected_official_twitter_handle', False)
    if positive_value_exists(elected_official_twitter_handle):
        elected_official_twitter_handle = extract_twitter_handle_from_text_string(elected_official_twitter_handle)
    elected_official_url = request.POST.get('elected_official_url', False)
    political_party = request.POST.get('political_party', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    maplight_id = request.POST.get('maplight_id', False)
    state_code = request.POST.get('state_code', False)
    elected_official_we_vote_id = request.POST.get('elected_official_we_vote_id', False)

    # Check to see if this elected_official is already being used anywhere
    elected_official_on_stage_found = False
    elected_official_on_stage = ElectedOfficial()
    if positive_value_exists(elected_official_id):
        try:
            elected_official_query = ElectedOfficial.objects.filter(id=elected_official_id)
            if len(elected_official_query):
                elected_official_on_stage = elected_official_query[0]
                elected_official_on_stage_found = True
        except Exception as e:
            pass

    # Check to see if there is a duplicate elected_official already saved for this election
    existing_elected_official_found = False
    if not positive_value_exists(elected_official_id):
        try:
            filter_list = Q()

            at_least_one_filter = False
            if positive_value_exists(vote_smart_id):
                at_least_one_filter = True
                filter_list |= Q(vote_smart_id=vote_smart_id)
            if positive_value_exists(maplight_id):
                at_least_one_filter = True
                filter_list |= Q(maplight_id=maplight_id)
            if positive_value_exists(elected_official_twitter_handle):
                at_least_one_filter = True
                filter_list |= Q(elected_official_twitter_handle=elected_official_twitter_handle)

            if at_least_one_filter:
                elected_official_duplicates_query = ElectedOfficial.objects.filter(filter_list)

                if len(elected_official_duplicates_query):
                    existing_elected_official_found = True
        except Exception as e:
            pass

    try:
        if existing_elected_official_found:
            messages.add_message(request, messages.ERROR, 'This elected_official is already saved for this election.')
            url_variables = "?elected_official_name=" + str(elected_official_name) + \
                            "&state_code=" + str(state_code) + \
                            "&google_civic_elected_official_name=" + str(google_civic_elected_official_name) + \
                            "&elected_official_twitter_handle=" + str(elected_official_twitter_handle) + \
                            "&elected_official_url=" + str(elected_official_url) + \
                            "&political_party=" + str(political_party) + \
                            "&vote_smart_id=" + str(vote_smart_id) + \
                            "&elected_official_we_vote_id=" + str(elected_official_we_vote_id) + \
                            "&maplight_id=" + str(maplight_id)
            return HttpResponseRedirect(reverse('elected_official:elected_official_new', args=()) + url_variables)
        elif elected_official_on_stage_found:
            # Update
            if elected_official_name is not False:
                elected_official_on_stage.elected_official_name = elected_official_name
            if state_code is not False:
                elected_official_on_stage.state_code = state_code
            if google_civic_elected_official_name is not False:
                elected_official_on_stage.google_civic_elected_official_name = google_civic_elected_official_name
            if elected_official_twitter_handle is not False:
                elected_official_on_stage.elected_official_twitter_handle = elected_official_twitter_handle
            if elected_official_url is not False:
                elected_official_on_stage.elected_official_url = elected_official_url
            if political_party is not False:
                political_party = convert_to_political_party_constant(political_party)
                elected_official_on_stage.political_party = political_party
            if vote_smart_id is not False:
                elected_official_on_stage.vote_smart_id = vote_smart_id
            if maplight_id is not False:
                elected_official_on_stage.maplight_id = maplight_id

            elected_official_on_stage.save()
            messages.add_message(request, messages.INFO, 'Elected Official updated.')
        else:
            # Create new

            required_elected_official_variables = True \
                if positive_value_exists(elected_official_name) \
                else False
            if required_elected_official_variables:
                elected_official_on_stage = ElectedOfficial(
                    elected_official_name=elected_official_name,
                    state_code=state_code,
                )
                if google_civic_elected_official_name is not False:
                    elected_official_on_stage.google_civic_elected_official_name = google_civic_elected_official_name
                if elected_official_twitter_handle is not False:
                    elected_official_on_stage.elected_official_twitter_handle = elected_official_twitter_handle
                if elected_official_url is not False:
                    elected_official_on_stage.elected_official_url = elected_official_url
                if political_party is not False:
                    political_party = convert_to_political_party_constant(political_party)
                    elected_official_on_stage.political_party = political_party
                if vote_smart_id is not False:
                    elected_official_on_stage.vote_smart_id = vote_smart_id
                if maplight_id is not False:
                    elected_official_on_stage.maplight_id = maplight_id
                if elected_official_we_vote_id is not False:
                    elected_official_on_stage.we_vote_id = elected_official_we_vote_id

                elected_official_on_stage.save()
                elected_official_id = elected_official_on_stage.id
                messages.add_message(request, messages.INFO, 'New elected_official saved.')
            else:
                # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
                url_variables = "?elected_official_name=" + str(elected_official_name) + \
                                "&state_code=" + str(state_code) + \
                                "&google_civic_elected_official_name=" + str(google_civic_elected_official_name) + \
                                "&elected_official_twitter_handle=" + str(elected_official_twitter_handle) + \
                                "&elected_official_url=" + str(elected_official_url) + \
                                "&political_party=" + str(political_party) + \
                                "&vote_smart_id=" + str(vote_smart_id) + \
                                "&elected_official_we_vote_id=" + str(elected_official_we_vote_id) + \
                                "&maplight_id=" + str(maplight_id)
                if positive_value_exists(elected_official_id):
                    return HttpResponseRedirect(reverse('elected_official:elected_official_edit',
                                                        args=(elected_official_id,)) + url_variables)
                else:
                    return HttpResponseRedirect(reverse('elected_official:elected_official_new', args=()) +
                                                url_variables)

    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save elected_official.')
        return HttpResponseRedirect(reverse('elected_official:elected_official_edit', args=(elected_official_id,)))

    if elected_official_id:
        return HttpResponseRedirect(reverse('elected_official:elected_official_edit', args=(elected_official_id,)))
    else:
        return HttpResponseRedirect(reverse('elected_official:elected_official_new', args=()))


@login_required
def elected_official_retrieve_photos_view(request, candidate_id):  # TODO DALE Transition fully to elected_official
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
def elected_official_delete_process_view(request):  # TODO DALE Transition fully to elected_official
    """
    Delete this elected_official
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    elected_official_id = convert_to_int(request.GET.get('elected_official_id', 0))

    # Retrieve this elected_official
    elected_official_on_stage_found = False
    elected_official_on_stage = ElectedOfficial()
    if positive_value_exists(elected_official_id):
        try:
            elected_official_query = ElectedOfficial.objects.filter(id=elected_official_id)
            if len(elected_official_query):
                elected_official_on_stage = elected_official_query[0]
                elected_official_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find elected_official -- exception.')

    if not elected_official_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find elected_official.')
        return HttpResponseRedirect(reverse('elected_official:elected_official_list', args=()))

    try:
        # Delete the elected_official
        elected_official_on_stage.delete()
        messages.add_message(request, messages.INFO, 'Elected Official deleted.')
        return HttpResponseRedirect(reverse('elected_official:elected_official_list', args=()))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete elected_official -- exception.')
        return HttpResponseRedirect(reverse('elected_official:elected_official_edit', args=(elected_official_id,)))
