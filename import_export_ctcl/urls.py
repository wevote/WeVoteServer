# import_export_ctcl/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path
from . import views_admin


urlpatterns = [
    re_path(r'^$', views_admin.import_export_ctcl_index_view, name='import_export_ctcl_index'),
    # re_path(r'^electoral_district_import_from_xml_view/$', views_admin.electoral_district_import_from_xml_view,
    #     name='electoral_district_import_from_xml_view'),
    re_path(r'^import_ctcl_from_xml/', views_admin.import_ctcl_from_xml_view,
        name='import_ctcl_from_xml'),
]
