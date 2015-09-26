# config/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.shortcuts import render

# from politician.models import Politician
# from election_office_measure.models import BallotItem


def start_view(request):
    template_values = {
        'hello_world': "hello world",
    }
    return render(request, 'templates/start.html', template_values)
