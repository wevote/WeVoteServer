# office_held/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.office_held_list_view, name='office_held_list', ),
    re_path(r'^delete/$', views_admin.office_held_delete_process_view, name='office_held_delete_process'),
    re_path(r'^edit_process/$', views_admin.office_held_edit_process_view, name='office_held_edit_process'),
    re_path(r'^location_list/$', views_admin.offices_held_for_location_list_view, name='offices_held_location_list'),
    re_path(r'^new/$', views_admin.office_held_new_view, name='office_held_new'),
    re_path(r'^import/$',
            views_admin.office_held_import_from_master_server_view, name='office_held_import_from_master_server'),
    re_path(r'^import_for_location/$',
            views_admin.offices_held_for_location_import_from_master_server_view,
            name='offices_held_for_location_import_from_master_server'),
    re_path(r'^real_time_status/$', views_admin.office_held_update_status, name='office_held_update_status'),
    re_path(r'^(?P<office_held_id>[0-9]+)/edit/$', views_admin.office_held_edit_view, name='office_held_edit'),
    re_path(r'^(?P<office_held_we_vote_id>wv[\w]{2}officeheld[\w]+)/summary/$',
            views_admin.office_held_summary_view, name='office_held_summary'),

]
