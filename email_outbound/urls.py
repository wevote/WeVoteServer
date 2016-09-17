# email_outbound/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^$', views_admin.batches_home_view, name='batches_home',),
    url(r'^batch_action_list/$', views_admin.batch_action_list_view, name='batch_action_list'),
    url(r'^batch_action_list_process/$', views_admin.batch_action_list_process_view, name='batch_action_list_process'),
    url(r'^batch_list/$', views_admin.batch_list_view, name='batch_list'),
    url(r'^batch_list_process/$', views_admin.batch_list_process_view, name='batch_list_process'),
]
