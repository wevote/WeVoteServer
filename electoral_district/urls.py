# electoral_district/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import url


urlpatterns = [
    # views_admin
    # url(r'^$', views_admin.electoral_district_index_view, name='electoral_district_index',),
    url(r'^electoral_district_import_from_xml_view/$',
        views_admin.electoral_district_import_from_xml_view, name='electoral_district_import_from_xml'),
]