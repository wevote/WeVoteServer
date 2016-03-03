# voter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Voter, VoterDeviceLinkManager
from admin_tools.views import redirect_to_sign_in_page
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from voter.models import fetch_voter_id_from_voter_device_link, voter_has_authority, voter_setup
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_api_device_id, set_voter_api_device_id, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def login_complete_view(request):
    try:
        voter_api_device_id = get_voter_api_device_id(request)
        if not positive_value_exists(voter_api_device_id):
            messages.add_message(request, messages.INFO, 'Missing voter_api_device_id.')
            return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

        voter_object = request.user
        if not voter_object:
            messages.add_message(request, messages.INFO, 'Missing voter.')
            return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

        # TODO Write the Twitter or Facebook information to the voter table so we can access it via the APIs
        # Currently all of the twitter authentication for Django is in the separate social_auth* tables

        # Relink this voter_api_device_id to this Voter account
        voter_device_manager = VoterDeviceLinkManager()
        voter_device_link_results = voter_device_manager.retrieve_voter_device_link(voter_api_device_id)
        voter_device_link = voter_device_link_results['voter_device_link']

        update_voter_device_link_results = voter_device_manager.update_voter_device_link(
           voter_device_link, voter_object)
        if update_voter_device_link_results['voter_device_link_updated']:
            messages.add_message(request, messages.INFO, 'Voter updated.')
        else:
            messages.add_message(request, messages.INFO, 'Voter could not be relinked.')
    except:
        messages.add_message(request, messages.INFO, 'Voter not updated.')

    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))


# This is open to anyone, and provides psql to update the database directly
def voter_authenticate_manually_view(request):
    messages_on_stage = get_messages(request)

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    store_new_voter_api_device_id_in_cookie = False
    if not positive_value_exists(voter_api_device_id):
        # Create a voter_device_id and voter in the database if one doesn't exist yet
        results = voter_setup(request)
        voter_api_device_id = results['voter_device_id']
        store_new_voter_api_device_id_in_cookie = results['store_new_voter_device_id_in_cookie']

    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    voter_id = convert_to_int(voter_id)
    voter_on_stage_found = False
    voter_on_stage = Voter()
    try:
        voter_on_stage = Voter.objects.get(id=voter_id)
        voter_on_stage_found = True
    except Voter.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Voter.DoesNotExist:
        # This is fine, we will display an error
        pass

    if voter_on_stage_found:
        set_this_voter_as_admin = "UPDATE voter_voter SET is_admin=True WHERE id={voter_id};".format(voter_id=voter_id)
        unset_this_voter_as_admin = "UPDATE voter_voter SET is_admin=False WHERE id={voter_id};".format(voter_id=voter_id)

        set_as_verified_volunteer = "UPDATE voter_voter SET is_verified_volunteer=True WHERE id={voter_id};" \
                                    "".format(voter_id=voter_id)
        unset_as_verified_volunteer = "UPDATE voter_voter SET is_verified_volunteer=False WHERE id={voter_id};" \
                                      "".format(voter_id=voter_id)
        template_values = {
            'messages_on_stage':            messages_on_stage,
            'voter':                        voter_on_stage,
            'voter_api_device_id':          voter_api_device_id,
            'is_authenticated':             request.user.is_authenticated(),
            'set_this_voter_as_admin':      set_this_voter_as_admin,
            'unset_this_voter_as_admin':    unset_this_voter_as_admin,
            'set_as_verified_volunteer':    set_as_verified_volunteer,
            'unset_as_verified_volunteer':  unset_as_verified_volunteer,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,

        }
    response = render(request, 'voter/voter_authenticate_manually.html', template_values)

    # We want to store the voter_api_device_id cookie if it is new
    # if positive_value_exists(voter_api_device_id) and positive_value_exists(store_new_voter_api_device_id_in_cookie):
    # DALE 2016-02-15 Always set if we have a voter_api_device_id
    if positive_value_exists(voter_api_device_id):
        set_voter_api_device_id(request, response, voter_api_device_id)

    return response


# This is open to anyone, and provides psql to update the database directly
def voter_authenticate_manually_process_view(request):
    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)

    voter_id = convert_to_int(voter_id)
    voter_signed_in = False
    try:
        voter_on_stage = Voter.objects.get(id=voter_id)
        # If the account associated with this voter_api_device_id is an admin, complete Django authentication
        if voter_on_stage.is_admin:
            voter_on_stage.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, voter_on_stage)
            messages.add_message(request, messages.INFO, 'Voter logged in.')
            voter_signed_in = True
        else:
            messages.add_message(request, messages.INFO, 'This account does not have Admin access.')
    except Voter.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'More than one voter found. Voter not logged in.')
    except Voter.DoesNotExist:
        # This is fine, we will display an error
        messages.add_message(request, messages.ERROR, 'Voter not found. Voter not logged in.')

    if voter_signed_in:
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))
    else:
        return HttpResponseRedirect(reverse('voter:authenticate_manually', args=()))


@login_required
def voter_edit_process_view(request):
    """
    Process the new or edit voter forms
    :param request:
    :return:
    """
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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
            messages.add_message(request, messages.INFO, 'Voter information updated.')
        else:
            # Create new
            messages.add_message(request, messages.INFO, 'We do not support adding new Voters.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save voter.')

    return HttpResponseRedirect(reverse('voter:voter_list', args=()))


@login_required
def voter_edit_view(request, voter_id):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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


@login_required
def voter_list_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    voter_id = convert_to_int(voter_id)

    messages_on_stage = get_messages(request)
    voter_list = Voter.objects.order_by('-last_login')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'voter_list': voter_list,
        'voter_id_signed_in': voter_id,
    }
    return render(request, 'voter/voter_list.html', template_values)


@login_required
def voter_summary_view(request, voter_id):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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
