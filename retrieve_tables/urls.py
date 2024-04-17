# office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from retrieve_tables.controllers_local import retrieve_sql_files_from_master_server
from retrieve_tables.controllers_master import fast_load_status_retrieve

urlpatterns = [
    # views_admin
    re_path(r'^import/status/$', fast_load_status_retrieve, name='fast_load_status_retrieve'),
    re_path(r'^import/files/$', retrieve_sql_files_from_master_server, name='retrieve_sql_files_from_master_server'),
]
