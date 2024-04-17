# import_export_maplight/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.import_export_maplight_index_view, name='import_export_maplight_index'),
    re_path(r'^import_maplight_from_json_view/', views_admin.import_maplight_from_json_view,
        name='import_maplight_from_json_view'),
    re_path(r'^transfer_from_maplight/', views_admin.transfer_maplight_data_to_we_vote_tables,
        name='transfer_from_maplight'),
]
