# party/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^party_import_from_xml_view/$',
        views_admin.party_import_from_xml_view, name='party_import_from_xml'),
]