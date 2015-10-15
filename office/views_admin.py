# office/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_deleted_exception, handle_record_not_found_exception, handle_record_not_saved_exception
from .models import ContestOffice
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import ContestOfficeSerializer
import wevote_functions.admin
from wevote_functions.models import convert_to_int


logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class ExportContestOfficeDataView(APIView):
    def get(self, request, format=None):
        contest_office_list = ContestOffice.objects.all()
        serializer = ContestOfficeSerializer(contest_office_list, many=True)
        return Response(serializer.data)


# @login_required()  # Commented out while we are developing login process()
def office_list_view(request):
    messages_on_stage = get_messages(request)
    office_list = ContestOffice.objects.order_by('office_name')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'office_list': office_list,
    }
    return render(request, 'office/office_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def office_new_view(request):
    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'office/office_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def office_edit_view(request, office_id):
    messages_on_stage = get_messages(request)
    office_id = convert_to_int(office_id)
    office_on_stage_found = False
    try:
        office_on_stage = ContestOffice.objects.get(id=office_id)
        office_on_stage_found = True
    except ContestOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestOffice.DoesNotExist:
        # This is fine, create new
        pass

    if office_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'office': office_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'office/office_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def office_edit_process_view(request):
    """
    Process the new or edit office forms
    :param request:
    :return:
    """
    office_id = convert_to_int(request.POST['office_id'])
    office_name = request.POST['office_name']
    twitter_handle = request.POST['twitter_handle']
    office_website = request.POST['office_website']

    # Check to see if this office is already being used anywhere
    office_on_stage_found = False
    try:
        office_query = ContestOffice.objects.filter(id=office_id)
        if len(office_query):
            office_on_stage = office_query[0]
            office_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if office_on_stage_found:
            # Update
            office_on_stage.office_name = office_name
            office_on_stage.twitter_handle = twitter_handle
            office_on_stage.office_website = office_website
            office_on_stage.save()
            messages.add_message(request, messages.INFO, 'ContestOffice updated.')
        else:
            # Create new
            office_on_stage = ContestOffice(
                office_name=office_name,
                twitter_handle=twitter_handle,
                office_website=office_website,
            )
            office_on_stage.save()
            messages.add_message(request, messages.INFO, 'New office saved.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save office.')

    return HttpResponseRedirect(reverse('office:office_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def office_summary_view(request, office_id):
    messages_on_stage = get_messages(request)
    office_id = convert_to_int(office_id)
    office_on_stage_found = False
    try:
        office_on_stage = ContestOffice.objects.get(id=office_id)
        office_on_stage_found = True
    except ContestOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestOffice.DoesNotExist:
        # This is fine, create new
        pass

    if office_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'office': office_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'office/office_summary.html', template_values)
