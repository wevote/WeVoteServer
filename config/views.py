# config/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render


def favicon_view(request):
    """
    Response for favicon.ico requests
    :param request:
    :return:
    """
    img = open('apis_v1/static/apis_v1/favicon.ico', 'rb')
    response = FileResponse(img)
    return response


def health_view(request):
    """
    A very simple health check that the load balancers use to make sure the site is running
    :param request:
    :return:
    """
    return HttpResponse("1", content_type='text/html')


def robots_view(request):
    """
    Response for robots.txt requests
    :param request:
    :return:
    """
    template_values = {
    }
    return render(request, 'admin/robots.txt', template_values)


def start_view(request):
    return HttpResponseRedirect(reverse('apis_v1:apisIndex', args=()))
