# measure/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.measure_list_view, name='measure_list',),
    url(r'^edit_process/$', views_admin.measure_edit_process_view, name='measure_edit_process'),
    # url(r'^export/', views_admin.MeasuresSyncOutView.as_view(), name='measures_export'),
    url(r'^import/$',
        views_admin.measures_import_from_master_server_view, name='measures_import_from_master_server'),
    url(r'^new/$', views_admin.measure_new_view, name='measure_new'),
    url(r'^(?P<measure_id>[0-9]+)/edit/$', views_admin.measure_edit_view, name='measure_edit'),
    url(r'^(?P<measure_id>[0-9]+)/summary/$', views_admin.measure_summary_view, name='measure_summary'),
]
