# config/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib.messages import get_messages
from django.shortcuts import render


def start_view(request):
    template_values = {
        'hello_world': "hello world",
    }
    return render(request, 'start.html', template_values)


def login_view(request):
    next = request.GET.get('next', '/')
    messages_on_stage = get_messages(request)
    template_values = {
        'next': next,
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'wevote_social/login.html', template_values)
