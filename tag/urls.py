# tag/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.tag_list_view, name='tag_list',),
    re_path(r'^new/$', views.tag_new_view, name='tag_new'),
    re_path(r'^new_process/$', views.tag_new_process_view, name='tag_new_process'),
]
