# admin_tools/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.admin_home_view, name='admin_home',),
    url(r'^data_cleanup/$', views.data_cleanup_view, name='data_cleanup'),
    url(r'^data_cleanup_organization_analysis/$',
        views.data_cleanup_organization_analysis_view, name='data_cleanup_organization_analysis'),
    url(r'^data_cleanup_organization_list_analysis/$',
        views.data_cleanup_organization_list_analysis_view, name='data_cleanup_organization_list_analysis'),
    url(r'^data_cleanup_position_list_analysis/$',
        views.data_cleanup_position_list_analysis_view, name='data_cleanup_position_list_analysis'),
    url(r'^data_cleanup_voter_hanging_data_process/$',
        views.data_cleanup_voter_hanging_data_process_view, name='data_cleanup_voter_hanging_data_process'),
    url(r'^data_cleanup_voter_list_analysis/$',
        views.data_cleanup_voter_list_analysis_view, name='data_cleanup_voter_list_analysis'),
    url(r'^import_sample_data/$', views.import_sample_data_view, name='import_sample_data'),
    url(r'^statistics/$', views.statistics_summary_view, name='statistics_summary'),
    url(r'^sync_dashboard/$', views.sync_data_with_master_servers_view, name='sync_dashboard'),
]
