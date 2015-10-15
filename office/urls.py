# office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.office_list_view, name='office_list',),
    url(r'^edit_process/$', views_admin.office_edit_process_view, name='office_edit_process'),
    url(r'^export/', views_admin.ExportContestOfficeDataView.as_view(), name='offices_export'),
    url(r'^new/$', views_admin.office_new_view, name='office_new'),
    url(r'^(?P<office_id>[0-9]+)/edit/$', views_admin.office_edit_view, name='office_edit'),
    url(r'^(?P<office_id>[0-9]+)/summary/$', views_admin.office_summary_view, name='office_summary'),
]
