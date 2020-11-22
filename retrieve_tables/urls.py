# office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import controllers

urlpatterns = [
    # views_admin
    url(r'^import/$',
        controllers.retrieve_sql_files_from_master_server, name='retrieve_sql_files_from_master_server'),
]
