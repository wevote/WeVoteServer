# electoral_district/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import re_path


urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.electoral_district_list_view, name='electoral_district_list',),
    re_path(r'^electoral_district_import_from_xml_view/$',
        views_admin.electoral_district_import_from_xml_view, name='electoral_district_import_from_xml'),
    re_path(r'^summary/$',
        views_admin.electoral_district_summary_view, name='electoral_district_summary'),
]
