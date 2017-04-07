# party/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import url


urlpatterns = [
    # views_admin
    url(r'^party_import_from_xml_view/$',
        views_admin.party_import_from_xml_view, name='party_import_from_xml'),
]