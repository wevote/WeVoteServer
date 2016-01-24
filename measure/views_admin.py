# measure/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


from .models import ContestMeasure
from .serializers import ContestMeasureSerializer
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
# from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import Election
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from rest_framework.views import APIView
from rest_framework.response import Response
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class ExportContestMeasureDataView(APIView):
    def get(self, request, format=None):
        contest_measure_list = ContestMeasure.objects.all()
        serializer = ContestMeasureSerializer(contest_measure_list, many=True)
        return Response(serializer.data)


# @login_required()  # Commented out while we are developing login process()
def measure_list_view(request):
    messages_on_stage = get_messages(request)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    try:
        measure_list = ContestMeasure.objects.order_by('measure_title')
        if positive_value_exists(google_civic_election_id):
            measure_list = measure_list.filter(google_civic_election_id=google_civic_election_id)
    except ContestMeasure.DoesNotExist:
        # This is fine
        measure_list = ContestMeasure()
        pass

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'measure_list': measure_list,
        'election_list': election_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'measure/measure_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def measure_new_view(request):
    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'measure/measure_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def measure_edit_view(request, measure_id):
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
            'messages_on_stage': messages_on_stage,
            'measure': measure_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'measure/measure_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def measure_edit_process_view(request):
    """
    Process the new or edit measure forms
    :param request:
    :return:
    """
    measure_id = convert_to_int(request.POST['measure_id'])
    measure_name = request.POST['measure_name']
    twitter_handle = request.POST['twitter_handle']
    measure_website = request.POST['measure_website']

    # Check to see if this measure is already being used anywhere
    measure_on_stage_found = False
    measure_on_stage = ContestMeasure()
    try:
        measure_query = ContestMeasure.objects.filter(id=measure_id)
        if len(measure_query):
            measure_on_stage = measure_query[0]
            measure_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if measure_on_stage_found:
            # Update
            measure_on_stage.measure_name = measure_name
            measure_on_stage.twitter_handle = twitter_handle
            measure_on_stage.measure_website = measure_website
            measure_on_stage.save()
            messages.add_message(request, messages.INFO, 'ContestMeasure updated.')
        else:
            # Create new
            measure_on_stage = ContestMeasure(
                measure_name=measure_name,
                twitter_handle=twitter_handle,
                measure_website=measure_website,
            )
            measure_on_stage.save()
            messages.add_message(request, messages.INFO, 'New measure saved.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save measure.')

    return HttpResponseRedirect(reverse('measure:measure_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def measure_summary_view(request, measure_id):
    messages_on_stage = get_messages(request)
    measure_id = convert_to_int(measure_id)
    measure_on_stage_found = False
    measure_on_stage = ContestMeasure()
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
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
