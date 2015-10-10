# config/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from django.shortcuts import render
from django.views.decorators.cache import cache_control
# from politician.models import Politician
# from election.models import BallotItem


def start_view(request):
    template_values = {
        'hello_world': "hello world",
    }
    return render(request, 'start.html', template_values)
