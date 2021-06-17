# measure/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.measure_list_view, name='measure_list',),
    re_path(r'^compare_two_measures/$',
        views_admin.compare_two_measures_for_merge_view, name='compare_two_measures_for_merge'),
    re_path(r'^duplicate_measures/$',
        views_admin.find_and_merge_duplicate_measures_view, name='find_and_merge_duplicate_measures'),
    re_path(r'^edit_process/$', views_admin.measure_edit_process_view, name='measure_edit_process'),
    # re_path(r'^export/', views_admin.MeasuresSyncOutView.as_view(), name='measures_export'),
    re_path(r'^import/$',
        views_admin.measures_import_from_master_server_view, name='measures_import_from_master_server'),
    re_path(r'^merge/$', views_admin.measure_merge_process_view, name='measure_merge_process'),
    re_path(r'^new/$', views_admin.measure_new_view, name='measure_new'),
    re_path(r'^(?P<measure_id>[0-9]+)/edit/$', views_admin.measure_edit_view, name='measure_edit'),
    re_path(r'^(?P<measure_we_vote_id>wv[\w]{2}meas[\w]+)/edit/$',
        views_admin.measure_edit_view, name='measure_edit_we_vote_id'),
    re_path(r'^(?P<measure_id>[0-9]+)/summary/$', views_admin.measure_summary_view, name='measure_summary'),
]
