# quick_info/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import QuickInfo, LANGUAGE_CHOICES
from .serializers import QuickInfoSerializer
from candidate.models import CandidateCampaign
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
# from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import Election
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from measure.models import ContestMeasure
from office.models import ContestOffice
from rest_framework.views import APIView
from rest_framework.response import Response
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class ExportQuickInfoDataView(APIView):
    def get(self, request, format=None):
        quick_info_list = QuickInfo.objects.all()
        serializer = QuickInfoSerializer(quick_info_list, many=True)
        return Response(serializer.data)


# @login_required()  # Commented out while we are developing login process()
def quick_info_list_view(request):
    messages_on_stage = get_messages(request)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    quick_info_list = QuickInfo.objects.order_by('id')  # This order_by is temp
    if positive_value_exists(google_civic_election_id):
        quick_info_list = QuickInfo.objects.filter(google_civic_election_id=google_civic_election_id)

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'quick_info_list': quick_info_list,
        'election_list': election_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'quick_info/quick_info_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_new_view(request):
    messages_on_stage = get_messages(request)

    election_list = Election.objects.order_by('-election_day_text')

    google_civic_election_id = 4162
    contest_office_options = ContestOffice.objects.order_by('office_name')
    if positive_value_exists(google_civic_election_id):
        contest_office_options = contest_office_options.filter(google_civic_election_id=google_civic_election_id)

    candidate_campaign_options = CandidateCampaign.objects.order_by('candidate_name')
    if positive_value_exists(google_civic_election_id):
        candidate_campaign_options = candidate_campaign_options.filter(google_civic_election_id=google_civic_election_id)

    contest_measure_options = ContestMeasure.objects.order_by('measure_title')
    if positive_value_exists(google_civic_election_id):
        contest_measure_options = contest_measure_options.filter(google_civic_election_id=google_civic_election_id)

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'contest_office_options':       contest_office_options,
        'candidate_campaign_options':   candidate_campaign_options,
        'contest_measure_options':      contest_measure_options,
        'election_list':                election_list,
        'language_choices':             LANGUAGE_CHOICES,
    }
    return render(request, 'quick_info/quick_info_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_edit_view(request, quick_info_id):
    messages_on_stage = get_messages(request)
    quick_info_id = convert_to_int(quick_info_id)
    quick_info_on_stage_found = False
    try:
        quick_info_on_stage = QuickInfo.objects.get(id=quick_info_id)
        quick_info_on_stage_found = True
    except QuickInfo.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except QuickInfo.DoesNotExist:
        # This is fine, create new
        pass

    election_list = Election.objects.order_by('-election_day_text')


    if quick_info_on_stage_found:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            'election_list':        election_list,
            'quick_info':           quick_info_on_stage,
            'language_choices':     LANGUAGE_CHOICES,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            'election_list':        election_list,
            'language_choices':     LANGUAGE_CHOICES,
        }
    return render(request, 'quick_info/quick_info_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_edit_process_view(request):
    """
    Process the new or edit quick_info forms
    :param request:
    :return:
    """
    quick_info_id = convert_to_int(request.POST['quick_info_id'])
    quick_info_name = request.POST['quick_info_name']
    twitter_handle = request.POST['twitter_handle']
    quick_info_website = request.POST['quick_info_website']

    # Check to see if this quick_info is already being used anywhere
    quick_info_on_stage_found = False
    try:
        quick_info_query = QuickInfo.objects.filter(id=quick_info_id)
        if len(quick_info_query):
            quick_info_on_stage = quick_info_query[0]
            quick_info_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if quick_info_on_stage_found:
            # Update
            quick_info_on_stage.quick_info_name = quick_info_name
            quick_info_on_stage.twitter_handle = twitter_handle
            quick_info_on_stage.quick_info_website = quick_info_website
            quick_info_on_stage.save()
            messages.add_message(request, messages.INFO, 'CandidateCampaign updated.')
        else:
            # Create new
            quick_info_on_stage = QuickInfo(
                quick_info_name=quick_info_name,
                twitter_handle=twitter_handle,
                quick_info_website=quick_info_website,
            )
            quick_info_on_stage.save()
            messages.add_message(request, messages.INFO, 'New quick_info saved.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save quick_info.')

    return HttpResponseRedirect(reverse('quick_info:quick_info_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def quick_info_summary_view(request, quick_info_id):
    messages_on_stage = get_messages(request)
    quick_info_id = convert_to_int(quick_info_id)
    quick_info_on_stage_found = False
    try:
        quick_info_on_stage = QuickInfo.objects.get(id=quick_info_id)
        quick_info_on_stage_found = True
    except QuickInfo.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except QuickInfo.DoesNotExist:
        # This is fine, create new
        pass

    if quick_info_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'quick_info': quick_info_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'quick_info/quick_info_summary.html', template_values)

