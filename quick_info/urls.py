# quick_info/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path
from . import views, views_admin

urlpatterns = [
    # views_admin.py
    re_path(r'^$', views_admin.quick_info_list_view, name='quick_info_list',),
    re_path(r'^edit_process/$', views_admin.quick_info_edit_process_view, name='quick_info_edit_process'),
    re_path(r'^new/$', views_admin.quick_info_new_view, name='quick_info_new',),
    re_path(r'^(?P<quick_info_id>[0-9]+)/edit/$', views_admin.quick_info_edit_view, name='quick_info_edit'),
    re_path(r'^(?P<quick_info_id>[0-9]+)/summary/$', views_admin.quick_info_summary_view, name='quick_info_summary'),
    re_path(r'^master_edit_process/$',
        views_admin.quick_info_master_edit_process_view, name='quick_info_master_edit_process'),
    re_path(r'^master_list/$', views_admin.quick_info_master_list_view, name='quick_info_master_list',),
    re_path(r'^master_new/$', views_admin.quick_info_master_new_view, name='quick_info_master_new',),
    re_path(r'^(?P<quick_info_master_id>[0-9]+)/master_edit/$',
        views_admin.quick_info_master_edit_view, name='quick_info_master_edit'),

    # views.py
    ]
