# measure/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


from .controllers import measures_import_from_master_server
from .models import ContestMeasure
from admin_tools.views import redirect_to_sign_in_page
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from election.models import Election
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from position.models import OPPOSE, PositionListManager, SUPPORT
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP
from django.http import HttpResponse
import json

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# class MeasuresSyncOutView(APIView):
#     def get(self, request, format=None):
def measures_sync_out_view(request):  # measuresSyncOut
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    try:
        contest_measure_list = ContestMeasure.objects.all()
        if positive_value_exists(google_civic_election_id):
            contest_measure_list = contest_measure_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            contest_measure_list = contest_measure_list.filter(state_code__iexact=state_code)
        # serializer = ContestMeasureSerializer(contest_measure_list, many=True)
        # return Response(serializer.data)
        contest_measure_list_dict = contest_measure_list.values('we_vote_id', 'maplight_id', 'vote_smart_id',
                                                                'measure_title', 'measure_subtitle',
                                                                'measure_text', 'measure_url',
                                                                'google_civic_election_id', 'ocd_division_id',
                                                                'primary_party', 'district_name',
                                                                'district_scope', 'district_id', 'state_code',
                                                                'wikipedia_page_id', 'wikipedia_page_title',
                                                                'wikipedia_photo_url', 'ballotpedia_page_title',
                                                                'ballotpedia_photo_url')
        if contest_measure_list_dict:
            contest_measure_list_json = list(contest_measure_list_dict)
            return HttpResponse(json.dumps(contest_measure_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'CONTEST_MEASURE_LIST_MISSING'
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')



@login_required
def measures_import_from_master_server_view(request):  # GET '/m/import/?google_civic_election_id=nnn&state_code=xx'
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(google_civic_election_id):
        logger.error("measures_import_from_master_server_view did not receive a google_civic_election_id")

    results = measures_import_from_master_server(request, google_civic_election_id, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Measures import completed. '
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
def measure_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    measure_list_count = 0
    position_list_manager = PositionListManager()
    measure_list_modified = []
    try:
        measure_list = ContestMeasure.objects.order_by('measure_title')
        if positive_value_exists(google_civic_election_id):
            measure_list = measure_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            measure_list = measure_list.filter(state_code__iexact=state_code)
        measure_search = request.GET.get('measure_search', '')

        if positive_value_exists(measure_search):
            filters = []
            new_filter = Q(state_code__icontains=measure_search)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__icontains=measure_search)
            filters.append(new_filter)

            new_filter = Q(measure_title__icontains=measure_search)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                measure_list = measure_list.filter(final_filters)

        measure_list_count = measure_list.count()

        if positive_value_exists(google_civic_election_id):
            for one_measure in measure_list:
                support_and_oppose_total = 0
                # Find the count of Voters that support this candidate (Organizations are not included in this)
                one_measure.support_count = position_list_manager.fetch_voter_positions_count_for_contest_measure(
                    one_measure.id, "", SUPPORT)
                one_measure.oppose_count = position_list_manager.fetch_voter_positions_count_for_contest_measure(
                    one_measure.id, "", OPPOSE)
                support_and_oppose_total += one_measure.support_count
                support_and_oppose_total += one_measure.oppose_count

                if positive_value_exists(support_and_oppose_total):
                    percentage_of_oppose_number = one_measure.oppose_count / support_and_oppose_total * 100
                    one_measure.percentage_of_oppose = "%d" % percentage_of_oppose_number
                    percentage_of_support_number = one_measure.support_count / support_and_oppose_total * 100
                    one_measure.percentage_of_support = "%d" % percentage_of_support_number

                measure_list_modified.append(one_measure)
        else:
            measure_list_modified = measure_list

    except ContestMeasure.DoesNotExist:
        # This is fine
        measure_list_modified = []
        pass

    election_list = Election.objects.order_by('-election_day_text')

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    status_print_list = ""
    status_print_list += "measure_list_count: " + \
                         str(measure_list_count) + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'measure_list':             measure_list_modified,
        'election_list':            election_list,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
        'measure_search':           measure_search,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'measure/measure_list.html', template_values)


@login_required
def measure_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    try:
        measure_list = ContestMeasure.objects.order_by('measure_title')
        if positive_value_exists(google_civic_election_id):
            measure_list = measure_list.filter(google_civic_election_id=google_civic_election_id)
    except ContestMeasure.DoesNotExist:
        # This is fine
        measure_list = ContestMeasure()
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'measure_list':             measure_list,
    }
    return render(request, 'measure/measure_edit.html', template_values)


@login_required
def measure_edit_view(request, measure_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)
    measure_id = convert_to_int(measure_id)
    measure_on_stage_found = False
    try:
        measure_on_stage = ContestMeasure.objects.get(id=measure_id)
        measure_on_stage_found = True
    except ContestMeasure.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
        measure_on_stage = ContestMeasure()
    except ContestMeasure.DoesNotExist:
        # This is fine, create new
        measure_on_stage = ContestMeasure()
        pass

    if measure_on_stage_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'google_civic_election_id': google_civic_election_id,
            'measure':                  measure_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'google_civic_election_id': google_civic_election_id,
        }
    return render(request, 'measure/measure_edit.html', template_values)


@login_required
def measure_edit_process_view(request):
    """
    Process the new or edit measure forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    measure_id = convert_to_int(request.POST['measure_id'])
    measure_title = request.POST.get('measure_title', False)
    google_civic_measure_title = request.POST.get('google_civic_measure_title', False)
    measure_subtitle = request.POST.get('measure_subtitle', False)
    measure_text = request.POST.get('measure_text', False)
    measure_url = request.POST.get('measure_url', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    maplight_id = request.POST.get('maplight_id', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    state_code = request.POST.get('state_code', False)

    # Check to see if this measure exists
    measure_on_stage_found = False
    measure_on_stage = ContestMeasure()
    error = False
    try:
        if positive_value_exists(measure_id):
            measure_query = ContestMeasure.objects.filter(id=measure_id)
            if len(measure_query):
                measure_on_stage = measure_query[0]
                measure_on_stage_found = True
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'There was an error trying to find this measure.')
        error = True

    if not error:
        try:
            if measure_on_stage_found:
                # Update
                if measure_title is not False:
                    measure_on_stage.measure_title = measure_title
                if google_civic_measure_title is not False:
                    measure_on_stage.google_civic_measure_title = google_civic_measure_title
                if measure_subtitle is not False:
                    measure_on_stage.measure_subtitle = measure_subtitle
                if measure_text is not False:
                    measure_on_stage.measure_text = measure_text
                if measure_url is not False:
                    measure_on_stage.measure_url = measure_url
                if google_civic_election_id is not False:
                    measure_on_stage.google_civic_election_id = google_civic_election_id
                if maplight_id is not False:
                    measure_on_stage.maplight_id = maplight_id
                if vote_smart_id is not False:
                    measure_on_stage.vote_smart_id = vote_smart_id
                if state_code is not False:
                    measure_on_stage.state_code = state_code

                measure_on_stage.save()
                messages.add_message(request, messages.INFO, 'ContestMeasure updated.')
            else:
                # Create new
                measure_on_stage = ContestMeasure(
                    measure_title=measure_title,
                    google_civic_measure_title=google_civic_measure_title,
                    measure_subtitle=measure_subtitle,
                    measure_text=measure_text,
                    measure_url=measure_url,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    maplight_id=maplight_id,
                    vote_smart_id=vote_smart_id,
                )
                measure_on_stage.save()
                messages.add_message(request, messages.INFO, 'New measure saved.')
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not save measure.')

    return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def measure_summary_view(request, measure_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    measure_id = convert_to_int(measure_id)
    measure_on_stage_found = False
    measure_on_stage = ContestMeasure()
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    try:
        measure_on_stage = ContestMeasure.objects.get(id=measure_id)
        measure_on_stage_found = True
    except ContestMeasure.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestMeasure.DoesNotExist:
        # This is fine, create new
        pass

    election_list = Election.objects.order_by('-election_day_text')

    if measure_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'measure': measure_on_stage,
            'election_list': election_list,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'measure/measure_summary.html', template_values)
