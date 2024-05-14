# config/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import os
import re

from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

def favicon_view(request):
    """
    Response for favicon.ico requests
    :param request:
    :return:
    """
    img = open('apis_v1/static/v1/favicon.ico', 'rb')
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

def app_ads_view(request):
    """
    Response for app-ads.txt requests
    :param request:
    :return:
    """
    template_values = {
    }
    return render(request, 'admin/app-ads.txt', template_values)


def start_view(request):
    return HttpResponseRedirect(reverse('apis_v1:apisIndex', args=()))


def google_verification_view(request):
    template_values = {}
    dirlist = os.listdir(os.getcwd() + '/templates')
    r = re.compile("goog.*?html")
    newlist = list(filter(r.match, dirlist))
    if len(newlist) != 1:
        logger.error('google_verification_view found zero, or more than one, google-site-verification files')

    return render(request, newlist[0], template_values)
