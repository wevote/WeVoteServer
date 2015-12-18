# quick_info/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url
from . import views, views_admin

urlpatterns = [
    # admin_views.py
    url(r'^$', views_admin.quick_info_list_view, name='quick_info_list',),
    url(r'^edit_process/$', views_admin.quick_info_edit_process_view, name='quick_info_edit_process'),
    url(r'^export/', views_admin.ExportQuickInfoDataView.as_view(), name='quick_info_export'),
    url(r'^new/$', views_admin.quick_info_new_view, name='quick_info_new',),
    url(r'^(?P<quick_info_id>[0-9]+)/edit/$', views_admin.quick_info_edit_view, name='quick_info_edit'),
    url(r'^(?P<quick_info_id>[0-9]+)/summary/$', views_admin.quick_info_summary_view, name='quick_info_summary'),

    # views.py
    ]
