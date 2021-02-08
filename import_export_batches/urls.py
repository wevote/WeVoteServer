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
    url(r'^batch_action_list_update_or_create_process/$',
        views_admin.batch_action_list_update_or_create_process_view,
        name='batch_action_list_update_or_create_process'),
    # url(r'^batch_action_list_import_update_or_create_rows/$',
    #     views_admin.batch_action_list_import_update_or_create_rows,
    #     name='batch_action_list_import_update_or_create_rows'),
    url(r'^batch_header_mapping/$', views_admin.batch_header_mapping_view, name='batch_header_mapping'),
    url(r'^batch_header_mapping_process/$',
        views_admin.batch_header_mapping_process_view, name='batch_header_mapping_process'),
    url(r'^batch_list/$', views_admin.batch_list_view, name='batch_list'),
    url(r'^batch_list_process/$', views_admin.batch_list_process_view, name='batch_list_process'),
    url(r'^batch_set_list/$', views_admin.batch_set_list_view, name='batch_set_list'),
    url(r'^batch_set_list_process/$', views_admin.batch_set_list_process_view, name='batch_set_list_process'),
    url(r'^batch_set_batch_list/$', views_admin.batch_set_batch_list_view, name='batch_set_batch_list'),
    url(r'^batch_action_list_export/$', views_admin.batch_action_list_export_view, name='batch_action_list_export'),
    url(r'^batch_action_list_export_voters/$',
        views_admin.batch_action_list_export_voters_view, name='batch_action_list_export_voters'),
    url(r'^batch_row_action_list_export/$',
        views_admin.batch_row_action_list_export_view, name='batch_row_action_list_export'),
    url(r'^batch_process_list/$', views_admin.batch_process_list_view, name='batch_process_list',),
    url(r'^batch_process_log_entry_list/$',
        views_admin.batch_process_log_entry_list_view, name='batch_process_log_entry_list',),
    # DEPRECATE batch_process_next_steps
    url(r'^batch_process_next_steps/$',
        views_admin.batch_process_next_steps_view, name='batch_process_next_steps'),
    url(r'^batch_process_pause_toggle/$',
        views_admin.batch_process_pause_toggle_view, name='batch_process_pause_toggle', ),
    url(r'^batch_process_system_toggle/$',
        views_admin.batch_process_system_toggle_view, name='batch_process_system_toggle', ),
    url(r'^process_next_activity_notices/$',
        views_admin.process_next_activity_notices_view, name='process_next_activity_notices'),
    url(r'^process_next_ballot_items/$',
        views_admin.process_next_ballot_items_view, name='process_next_ballot_items'),
    url(r'^process_next_general_maintenance/$',
        views_admin.process_next_general_maintenance_view, name='process_next_general_maintenance'),
]
