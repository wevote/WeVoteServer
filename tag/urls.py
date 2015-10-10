# tag/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.tag_list_view, name='tag_list',),
    url(r'^new/$', views.tag_new_view, name='tag_new'),
    url(r'^new_process/$', views.tag_new_process_view, name='tag_new_process'),
]
