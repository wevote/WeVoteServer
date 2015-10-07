# apis_v1/views_docs.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.shortcuts import render


def apis_index_doc_view(request):
    """
    Show a list of available APIs
    """
    template_values = {
        # 'key': value,
    }
    return render(request, 'apis_v1/apis_index.html', template_values)


def device_id_generate_doc_view(request):
    """
    Show documentation about deviceIdGenerate
    """
    template_values = {
        # 'key': value,
    }
    return render(request, 'apis_v1/deviceIdGenerate.html', template_values)


def voter_count_doc_view(request):
    """
    Show documentation about voterCount
    """
    template_values = {
        # 'key': value,
    }
    return render(request, 'apis_v1/voterCount.html', template_values)


def voter_create_doc_view(request):
    """
    Show documentation about voterCreate
    """
    template_values = {
        # 'key': value,
    }
    return render(request, 'apis_v1/voterCreate.html', template_values)


def voter_retrieve_doc_view(request):
    """
    Show documentation about voterRetrieve
    """
    template_values = {
        # 'key': value,
    }
    return render(request, 'apis_v1/voterRetrieve.html', template_values)
