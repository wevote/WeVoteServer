# office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import controllers

urlpatterns = [
    # views_admin
    re_path(r'^import/status/$',
        controllers.fast_load_status_retrieve, name='fast_load_status_retrieve'),
    re_path(r'^import/files/$',
        controllers.retrieve_sql_files_from_master_server, name='retrieve_sql_files_from_master_server'),
]
