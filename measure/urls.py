# measure/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.measure_list_view, name='measure_list',),
    url(r'^compare_two_measures/$',
        views_admin.compare_two_measures_for_merge_view, name='compare_two_measures_for_merge'),
    url(r'^duplicate_measures/$',
        views_admin.find_and_merge_duplicate_measures_view, name='find_and_merge_duplicate_measures'),
    url(r'^edit_process/$', views_admin.measure_edit_process_view, name='measure_edit_process'),
    # url(r'^export/', views_admin.MeasuresSyncOutView.as_view(), name='measures_export'),
    url(r'^import/$',
        views_admin.measures_import_from_master_server_view, name='measures_import_from_master_server'),
    url(r'^merge/$', views_admin.measure_merge_process_view, name='measure_merge_process'),
    url(r'^new/$', views_admin.measure_new_view, name='measure_new'),
    url(r'^(?P<measure_id>[0-9]+)/edit/$', views_admin.measure_edit_view, name='measure_edit'),
    url(r'^(?P<measure_we_vote_id>wv[\w]{2}meas[\w]+)/edit/$',
        views_admin.measure_edit_view, name='measure_edit_we_vote_id'),
    url(r'^(?P<measure_id>[0-9]+)/summary/$', views_admin.measure_summary_view, name='measure_summary'),
]
