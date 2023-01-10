# office_held/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Q
from election.models import Election, ElectionManager
from office_held.models import OfficeHeld, OfficeHeldManager, OfficeHeldListManager
from representative.models import RepresentativeManager
import exception.models
from import_export_google_civic.controllers import retrieve_representatives_from_google_civic_api
import json
from polling_location.models import PollingLocationManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP

OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
office_held_status_string = ""

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def office_held_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    office_held_search = request.GET.get('office_held_search', '')

    office_held_list_found = False
    office_held_list = []
    updated_office_held_list = []
    office_held_list_count = 0
    try:
        office_held_queryset = OfficeHeld.objects.all()
        if positive_value_exists(google_civic_election_id):
            office_held_queryset = office_held_queryset.filter(google_civic_election_id=google_civic_election_id)
        else:
            # TODO Limit this search to upcoming_elections only
            pass
        if positive_value_exists(state_code):
            office_held_queryset = office_held_queryset.filter(state_code__iexact=state_code)
        office_held_queryset = office_held_queryset.order_by("office_held_name")

        if positive_value_exists(office_held_search):
            search_words = office_held_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                new_filter = Q(office_held_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(wikipedia_id__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    office_held_queryset = office_held_queryset.filter(final_filters)

        office_held_list = list(office_held_queryset)

        if len(office_held_list):
            office_held_list_found = True
            status = 'OFFICES_HELD_RETRIEVED'
            success = True
        else:
            status = 'NO_OFFICES_HELD_RETRIEVED'
            success = True
    except OfficeHeld.DoesNotExist:
        # No offices_held found. Not a problem.
        status = 'NO_OFFICES_HELD_FOUND_DoesNotExist'
        office_held_list = []
        success = True
    except Exception as e:
        status = 'FAILED retrieve_all_offices_held_for_upcoming_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    if office_held_list_found:
        for office_held in office_held_list:
            # TODO fetch representatives count instead candidate
            # office_held.candidate_count = fetch_candidate_count_for_office(office_held.id)
            updated_office_held_list.append(office_held)

            office_held_list_count = len(updated_office_held_list)
            if office_held_list_count >= 500:
                # Limit to showing only 500
                break

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

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    office_held_list_count_str = f'{office_held_list_count:,}'

    status_print_list = ""
    status_print_list += "office_held_list_count: " + office_held_list_count_str + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'office_held_list':      updated_office_held_list,
        'office_held_search':    office_held_search,
        'election_list':            election_list,
        'state_code':               state_code,
        'show_all_elections':       show_all_elections,
        'state_list':               sorted_state_list,
        'google_civic_election_id': google_civic_election_id,
        'status':                   status,
        success:                    success
    }
    return render(request, 'office_held/office_held_list.html', template_values)


@login_required
def office_held_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")

    office_held_list_manager = OfficeHeldListManager()
    updated_office_held_list = []
    results = office_held_list_manager.retrieve_all_offices_held_for_upcoming_election(
        google_civic_election_id, state_code, True)
    if results['office_held_list_found']:
        office_held_list = results['office_held_list_objects']
        # TODO fetch representatives count instead candidate
        # for office_held in office_held_list:
        #     office_held.candidate_count = fetch_candidate_count_for_office(office_held.id)
        #     updated_office_held_list.append(office_held)

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'office_held_list':      updated_office_held_list,
    }
    return render(request, 'office_held/office_held_edit.html', template_values)


@login_required
def office_held_edit_view(request, office_held_id=0, office_held_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    office_held_id = convert_to_int(office_held_id)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    office_held_on_stage = OfficeHeld()
    office_held_on_stage_found = False
    try:
        if positive_value_exists(office_held_id):
            office_held_on_stage = OfficeHeld.objects.get(id=office_held_id)
        else:
            office_held_on_stage = OfficeHeld.objects.get(we_vote_id=office_held_we_vote_id)
        office_held_on_stage_found = True
    except OfficeHeld.MultipleObjectsReturned as e:
        exception.models.handle_record_found_more_than_one_exception(e, logger=logger)
    except OfficeHeld.DoesNotExist:
        # This is fine, create new
        pass

    if office_held_on_stage_found:
        # Was a office_held_merge_possibility_found?
        office_held_on_stage.contest_office_merge_possibility_found = True  # TODO DALE Make dynamic
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'office_held':           office_held_on_stage,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'google_civic_election_id': google_civic_election_id,
        }
    return render(request, 'office_held/office_held_edit.html', template_values)


@login_required
def office_held_summary_view(request, office_held_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    office_held_id = convert_to_int(office_held_id)
    office_held_on_stage_found = False
    state_code = request.GET.get('state_code', "")
    try:
        office_held_on_stage = OfficeHeld.objects.get(id=office_held_id)
        office_held_on_stage_found = True
    except OfficeHeld.MultipleObjectsReturned as e:
        exception.models.handle_record_found_more_than_one_exception(e, logger=logger)
    except OfficeHeld.DoesNotExist:
        # This is fine, create new
        pass

    candidate_list_modified = []
    # position_list_manager = PositionListManager()

    election_list = Election.objects.order_by('-election_day_text')

    if office_held_on_stage_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'office_held':              office_held_on_stage,
            'candidate_list':           candidate_list_modified,
            'state_code':               state_code,
            'election_list':            election_list,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'office_held/office_held_summary.html', template_values)


@login_required
def office_held_edit_process_view(request):
    """
    Process the new or edit office held forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    office_held_id = convert_to_int(request.POST.get('office_held_id', 0))
    office_held_name = request.POST.get('office_held_name', False)
    google_civic_office_held_name = request.POST.get('google_civic_office_held_name', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    ocd_division_id = request.POST.get('ocd_division_id', False)
    primary_party = request.POST.get('primary_party', False)
    state_code = request.POST.get('state_code', False)
    # ballotpedia_office_id = request.POST.get('ballotpedia_office_id', False)
    # ballotpedia_office_name = request.POST.get('ballotpedia_office_name', False)
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    redirect_to_office_held_list = convert_to_int(request.POST['redirect_to_office_held_list'])

    election_state = ''
    if state_code is not False:
        election_state = state_code
    elif google_civic_election_id:
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            election_state = election.get_election_state()

    # Check to see if this office is already in the database
    office_held_on_stage_found = False
    office_held_on_stage = None
    try:
        office_held_query = OfficeHeld.objects.filter(id=office_held_id)
        if len(office_held_query):
            office_held_on_stage = office_held_query[0]
            office_held_on_stage_found = True
    except Exception as e:
        exception.models.handle_record_not_found_exception(e, logger=logger)

    try:
        if office_held_on_stage_found:
            # Update
            # Removed for now: convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and
            if office_held_name is not False:
                office_held_on_stage.office_held_name = office_held_name
            if google_civic_office_held_name is not False:
                office_held_on_stage.google_civic_office_held_name = google_civic_office_held_name
            if ocd_division_id is not False:
                office_held_on_stage.ocd_division_id = ocd_division_id
            if primary_party is not False:
                office_held_on_stage.primary_party = primary_party
            if election_state is not False:
                office_held_on_stage.state_code = election_state
            # if ballotpedia_office_id is not False:
            #     office_on_stage.ballotpedia_office_id = ballotpedia_office_id
            # if ballotpedia_office_name is not False:
            #     office_on_stage.ballotpedia_office_name = ballotpedia_office_name
            office_held_on_stage.save()
            office_held_on_stage_id = office_held_on_stage.id
            messages.add_message(request, messages.INFO, 'Office updated.')
            google_civic_election_id = office_held_on_stage.google_civic_election_id

            return HttpResponseRedirect(reverse('office_held:office_held_summary',
                                                args=(office_held_on_stage_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))
        else:
            # Create new
            office_held_on_stage = OfficeHeld(
                office_held_name=office_held_name,
                google_civic_election_id=google_civic_election_id,
                state_code=election_state,
            )
            # Removing this limitation: convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and
            if google_civic_office_held_name is not False:
                office_held_on_stage.google_civic_office_name = google_civic_office_held_name
            if ocd_division_id is not False:
                office_held_on_stage.ocd_division_id = ocd_division_id
            if primary_party is not False:
                office_held_on_stage.primary_party = primary_party
            # if ballotpedia_office_id is not False:
            #     office_on_stage.ballotpedia_office_id = ballotpedia_office_id
            # if ballotpedia_office_name is not False:
            #     office_on_stage.ballotpedia_office_name = ballotpedia_office_name
            office_held_on_stage.save()
            messages.add_message(request, messages.INFO, 'New office held saved.')

            # Come back to the "Create New Office" page
            return HttpResponseRedirect(reverse('office_held:office_held_new', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))
    except Exception as e:
        exception.models.handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save office held:' + str(e))

    if redirect_to_office_held_list:
        return HttpResponseRedirect(reverse('office_held:office_held_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))
    else:
        return HttpResponseRedirect(reverse('office_held:office_held_edit', args=(office_held_id,)))


@login_required
def office_held_delete_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    office_held_id = convert_to_int(request.GET.get('office_held_id', 0))
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    # office_held_on_stage_found = False
    office_held_on_stage = OfficeHeld()
    try:
        office_held_on_stage = OfficeHeld.objects.get(id=office_held_id)
        # office_held_on_stage_found = True
        google_civic_election_id = office_held_on_stage.google_civic_election_id
    except OfficeHeld.MultipleObjectsReturned:
        pass
    except OfficeHeld.DoesNotExist:
        pass

    # TODO fetch representatives instead candidate
    candidates_found_for_this_office = False
    # if office_held_on_stage_found:
    #     try:
    #         candidate_list = CandidateCampaign.objects.filter(contest_office_id=office_held_id)
    #         # if positive_value_exists(google_civic_election_id):
    #         #     candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
    #         candidate_list = candidate_list.order_by('candidate_name')
    #         if len(candidate_list):
    #             candidates_found_for_this_office = True
    #     except CandidateCampaign.DoesNotExist:
    #         pass

    try:
        if not candidates_found_for_this_office:
            # Delete the office
            office_held_on_stage.delete()
            messages.add_message(request, messages.INFO, 'Office Held deleted.')
        else:
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'candidates still attached to this office held.')
            return HttpResponseRedirect(reverse('office_held:office_held_summary', args=(office_held_id,)))
    except Exception:
        messages.add_message(request, messages.ERROR, 'Could not delete office held -- exception.')
        return HttpResponseRedirect(reverse('office_held:office_held_summary', args=(office_held_id,)))

    return HttpResponseRedirect(reverse('office_held:office_held_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def office_held_update_view(request, office_held_id=0, office_held_we_vote_id=""):
    # Get offices and officials from Google Civic API

    global office_held_status_string
    office_held_completion_status = ""
    offices_created = 0
    officials_created = 0

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('update_state_code', '')

    if not state_code:
        messages.add_message(request, messages.INFO, "Please select a state!")
    else:
        # Get all the map points that are in the current state, and extract the poll addresses from google civic
        try:
            officials_names = {}
            results = PollingLocationManager().retrieve_polling_locations_in_city_or_state(state_code, None, None)
            if results['polling_location_list_found']:
                polling_location_list = results['polling_location_list']
                number_of_polls = str(len(polling_location_list))
                print("polling_location_list size  " + number_of_polls)
                i = 0
                for polling_location in polling_location_list:
                    i= i + 1
                    # Get the address for this polling place, and then retrieve the ballot from Google Civic API
                    results = polling_location.get_text_for_map_search_results()
                    text_for_map_search = results['text_for_map_search']
                    json = retrieve_representatives_from_google_civic_api(text_for_map_search)
                    one_polling_location_json = json['structured_json']
                    if 'error' in one_polling_location_json:
                        # These errors can be as little as "Failed to parse address" or as big as "API Limits Exceeded"
                        message = one_polling_location_json.get("error").get("message", None)
                        code = one_polling_location_json.get("error").get("code", None)
                        txt = "Google Civic has returned API Errors: "
                        if message:
                            txt += message + ", code = " + str(code)
                        office_held_status_string = message
                        if code == 400:
                            office_held_status_string = message + ": '" + text_for_map_search + "'"
                            print("views_admin:" + office_held_status_string)
                            continue
                        elif code == 403:
                            office_held_completion_status = "Processed " + str(i) + " of " + number_of_polls + \
                                                               " map points for the state of " + state_code + \
                                                        ".  Ended in mid stream, since the API User Rate was exceeded"
                            break
                        else:
                            print("office held non-specific error: " + txt)
                            office_held_status_string = message
                    else:
                        office_held_status_string = \
                            "Location " + str(i) + " of " + number_of_polls + ", offices created " \
                             + str(offices_created) + ", officials created " + str(officials_created) + ", poll: " + \
                            text_for_map_search

                        office_held_completion_status = "Processed " + str(i) + " of " + number_of_polls + \
                                                           " map points for the state of " + state_code
                        # print(office_held_status_string)

                    divisions = one_polling_location_json['divisions']
                    offices  = one_polling_location_json['offices']
                    officials = one_polling_location_json['officials']
                    for official in officials:
                        google_civic_representative_name = political_party = representative_phone = \
                            representative_url = photo_url = google_plus_url = facebook_url = twitter_url = \
                            youtube_url = number_elected = google_civic_office_held_name = ocd_division_id = \
                            office_held_description = contest_level0 = division_name = ""
                        if 'name' in official:
                            google_civic_representative_name = official['name']
                            # 95%+ of the data for a state is duplicate, so don't process the official's name twice.
                            if google_civic_representative_name in officials_names:
                                continue
                            else:
                                officials_names[google_civic_representative_name] = 1
                        if 'party' in official:
                            political_party  = official['party']
                        if 'phones' in official:
                            representative_phone = official['phones'][0]
                        if 'urls' in official:
                            representative_url = official['urls'][0]
                        if 'photoUrl' in official:
                            photo_url = official['photoUrl']
                        if 'channels' in official:
                            channels = official['channels']
                            for channel in channels:
                                key = channel['type']
                                value = channel['id']
                                if key == "GooglePlus":  # Some Google+ id's are numbers like '108233445289196913395'
                                    google_plus_url = "https://plus.google.com/" + value
                                elif key == "Facebook":
                                    facebook_url = " https://www.facebook.com/" + value
                                elif key == "Twitter":
                                    twitter_url = "https://twitter.com/" + value
                                elif key == "YouTube":
                                    youtube_url = "https://www.youtube.com/" + value

                        index = officials.index(official)
                        for office in offices:
                            list_indices = office.get('officialIndices')
                            if index in list_indices:
                                number_elected = str(len(list_indices))
                                google_civic_office_held_name = office.get('name')   # United States Senate
                                ocd_division_id = office.get('divisionId')            # ocd-division/country:us/state:ca
                                if office.get('roles') and len(office.get('roles')) > 0:
                                    office_held_description = office.get('roles')[0] # legislatorUpperBody
                                if office.get('levels') and len(office.get('levels')) > 0:
                                    contest_level0 = office.get('levels')[0]            # country
                                division = divisions.get(ocd_division_id, None)
                                if division:
                                    division_name = division.get('name')                # United States
                                break

                        # This "print" has a dual purpose, it also slows us down enough to avoid api rate limitations
                        # for the "limited" google civic account that developers use
                        # print(">> " + google_civic_representative_name + ", " + political_party + ", " +
                        #       representative_phone + ", " + representative_url + ", " + photo_url + ", " +
                        #       google_plus_url + ", " + facebook_url + ", " + twitter_url + ", " + youtube_url + ", " +
                        #       number_elected + ", " + google_civic_office_held_name + ", " + ocd_division_id +
                        #       ", " + office_held_description + ", " + contest_level0 + ", " + division_name)

                        # Store the data
                        passed_state_code = ""   # The president and vp, should not have an associated state
                        if "state" in ocd_division_id:
                            passed_state_code = state_code

                        representative_name = google_civic_representative_name  # So something shows up on the page
                        official_results = RepresentativeManager().update_or_create_representative(
                                                          google_civic_office_held_name, representative_name,
                                                          google_civic_representative_name, political_party, photo_url,
                                                          ocd_division_id, passed_state_code,
                                                          representative_url,
                                                          facebook_url, twitter_url, google_plus_url, youtube_url,
                                                          representative_phone)

                        office_results = OfficeHeldManager().update_or_create_office_held(
                            google_civic_office_held_name, ocd_division_id, google_civic_office_held_name,
                            number_elected, passed_state_code, division_name, contest_level0,
                            office_held_description)

                        if office_results['new_office_created']:
                            offices_created = offices_created + 1
                        if official_results['new_representative_created']:
                            officials_created = officials_created + 1

        except Exception as e:
            print("Exception in get_offices_and_divisions e = ", e)

    office_held_completion_status += " (" + str(offices_created) + " Offices created, " + str(officials_created) + \
                                        " Officials created)"

    print("END of loop get_offices_and_divisions")

    messages.add_message(request, messages.INFO, office_held_completion_status)
    office_held_status_string = ""
    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
        'started_update':           'stop',
    }

    return render(request, 'office_held/office_held_list.html', template_values)


def office_held_update_status(request):
    global office_held_status_string

    if 'office_held_status_string' not in globals():
        office_held_status_string = ""

    json_data = {
        'text': office_held_status_string,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
