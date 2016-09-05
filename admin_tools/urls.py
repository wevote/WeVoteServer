# admin_tools/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.admin_home_view, name='admin_home',),
    url(r'^import_sample_data/$', views.import_sample_data_view, name='import_sample_data'),
    url(r'^statistics/$', views.statistics_summary_view, name='statistics_summary'),
    url(r'^sync_dashboard/$', views.sync_data_with_master_servers_view, name='sync_dashboard'),
]
