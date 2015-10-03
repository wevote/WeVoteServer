# apis_v1/views_docs.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.shortcuts import render


def apis_index(request):
    """
    Show a list of available APIs
    """
    template_values = {
        # 'key': value,
    }
    return render(request, 'apis_v1/apis_index.html', template_values)


def device_id_generate(request):
    """
    Show documentation about deviceIdGenerate
    """
    template_values = {
        # 'key': value,
    }
    return render(request, 'apis_v1/deviceIdGenerate.html', template_values)
