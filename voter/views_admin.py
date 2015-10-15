# voter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Voter
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from wevote_functions.models import convert_to_int
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


# @login_required()  # Commented out while we are developing login process()
def voter_edit_process_view(request):
    """
    Process the new or edit voter forms
    :param request:
    :return:
    """
    voter_id = convert_to_int(request.POST['voter_id'])
    voter_name = request.POST['voter_name']

    # Check to see if this voter is already being used anywhere
    voter_on_stage_found = False
    try:
        voter_query = Voter.objects.filter(id=voter_id)
        if len(voter_query):
            voter_on_stage = voter_query[0]
            voter_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if voter_on_stage_found:
            # Update
            voter_on_stage.voter_name = voter_name
            voter_on_stage.save()
            messages.add_message(request, messages.INFO, 'Voter updated.')
        else:
            # Create new
            messages.add_message(request, messages.INFO, 'We do not support adding new Voters.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save voter.')

    return HttpResponseRedirect(reverse('voter:voter_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def voter_edit_view(request, voter_id):
    messages_on_stage = get_messages(request)
    voter_id = convert_to_int(voter_id)
    voter_on_stage_found = False
    try:
        voter_on_stage = Voter.objects.get(id=voter_id)
        voter_on_stage_found = True
    except Voter.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Voter.DoesNotExist:
        # This is fine, create new
        pass

    if voter_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'voter': voter_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'voter/voter_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def voter_list_view(request):
    messages_on_stage = get_messages(request)
    voter_list = Voter.objects.order_by('-last_login')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'voter_list': voter_list,
    }
    return render(request, 'voter/voter_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def voter_summary_view(request, voter_id):
    messages_on_stage = get_messages(request)
    voter_id = convert_to_int(voter_id)
    voter_on_stage_found = False
    try:
        voter_on_stage = Voter.objects.get(id=voter_id)
        voter_on_stage_found = True
    except Voter.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Voter.DoesNotExist:
        # This is fine, create new
        pass

    if voter_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'voter': voter_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'voter/voter_summary.html', template_values)
