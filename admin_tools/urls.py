# admin_tools/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.admin_home_view, name='admin_home',),
    re_path(r'^data_cleanup/$', views.data_cleanup_view, name='data_cleanup'),
    re_path(r'^data_cleanup_organization_analysis/$',
        views.data_cleanup_organization_analysis_view, name='data_cleanup_organization_analysis'),
    re_path(r'^data_cleanup_organization_list_analysis/$',
        views.data_cleanup_organization_list_analysis_view, name='data_cleanup_organization_list_analysis'),
    re_path(r'^data_cleanup_position_list_analysis/$',
        views.data_cleanup_position_list_analysis_view, name='data_cleanup_position_list_analysis'),
    re_path(r'^data_cleanup_voter_hanging_data_process/$',
        views.data_cleanup_voter_hanging_data_process_view, name='data_cleanup_voter_hanging_data_process'),
    re_path(r'^data_cleanup_voter_list_analysis/$',
        views.data_cleanup_voter_list_analysis_view, name='data_cleanup_voter_list_analysis'),
    re_path(r'^data_voter_statistics/$', views.data_voter_statistics_view, name='data_voter_statistics'),
    re_path(r'^import_sample_data/$', views.import_sample_data_view, name='import_sample_data'),
    re_path(r'^statistics/$', views.statistics_summary_view, name='statistics_summary'),
    re_path(r'^sync_dashboard/$', views.sync_data_with_master_servers_view, name='sync_dashboard'),
]
