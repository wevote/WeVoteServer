# admin_tools/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.shortcuts import render


def admin_home(request):

    template_values = {

    }
    return render(request, 'admin_home/index.html', template_values)
