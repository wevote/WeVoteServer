# config/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect


def health_view(request):
    """
    A very simple health check that the load balancers use to make sure the site is running
    :param request:
    :return:
    """
    return HttpResponse("1", content_type='text/html')


def start_view(request):
    return HttpResponseRedirect(reverse('apis_v1:apisIndex', args=()))
