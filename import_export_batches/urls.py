# import_export_batches/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^$', views_admin.batches_home_view, name='batches_home',),
    url(r'^batch_action_list/$', views_admin.batch_action_list_view, name='batch_action_list'),
    url(r'^batch_action_list_analyze_process/$', views_admin.batch_action_list_analyze_process_view,
        name='batch_action_list_analyze_process'),
    url(r'^batch_action_list_assign_election_to_rows_process/$',
        views_admin.batch_action_list_assign_election_to_rows_process_view,
        name='batch_action_list_assign_election_to_rows_process'),
    url(r'^batch_action_list_create_or_update_process/$',
        views_admin.batch_action_list_create_or_update_process_view,
        name='batch_action_list_create_or_update_process'),
    # url(r'^batch_action_list_import_create_or_update_rows/$',
    #     views_admin.batch_action_list_import_create_or_update_rows,
    #     name='batch_action_list_import_create_or_update_rows'),
    url(r'^batch_header_mapping/$', views_admin.batch_header_mapping_view, name='batch_header_mapping'),
    url(r'^batch_header_mapping_process/$',
        views_admin.batch_header_mapping_process_view, name='batch_header_mapping_process'),
    url(r'^batch_list/$', views_admin.batch_list_view, name='batch_list'),
    url(r'^batch_list_process/$', views_admin.batch_list_process_view, name='batch_list_process'),
    url(r'^batch_set_list/$', views_admin.batch_set_list_view, name='batch_set_list'),
    url(r'^batch_set_list_process/$', views_admin.batch_set_list_process_view, name='batch_set_list_process'),
    url(r'^batch_set_batch_list/$', views_admin.batch_set_batch_list_view, name='batch_set_batch_list'),
    url(r'^batch_set_batch_list_export/$', views_admin.batch_action_list_export_view, name='batch_set_batch_list_export'),
]
