# office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import controllers

urlpatterns = [
    # views_admin
    re_path(r'^import/$',
        controllers.retrieve_sql_files_from_master_server, name='retrieve_sql_files_from_master_server'),
]
