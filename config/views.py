# config/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render


def start_view(request):
    return HttpResponseRedirect(reverse('apis_v1:apisIndex', args=()))

# I don't believe this is used
# def login_view(request):
#     next = request.GET.get('next', '/')
#
#     # Create a voter_device_id and voter in the database if one doesn't exist yet
#     results = voter_setup(request)
#     voter_device_id = results['voter_device_id']
#     store_new_voter_device_id_in_cookie = results['store_new_voter_device_id_in_cookie']
#
#     messages_on_stage = get_messages(request)
#     template_values = {
#         'next': next,
#         'messages_on_stage': messages_on_stage,
#     }
#     response = render(request, 'wevote_social/login.html', template_values)
#
#     # We want to store the voter_device_id cookie if it is new
#     if positive_value_exists(voter_device_id) and positive_value_exists(store_new_voter_device_id_in_cookie):
#         set_voter_device_id(request, response, voter_device_id)
#
#     return response
