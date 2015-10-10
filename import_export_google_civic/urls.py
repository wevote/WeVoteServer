# import_export_google_civic/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.import_voterinfo_from_json_view, name='import_voterinfo_from_json'),
]
