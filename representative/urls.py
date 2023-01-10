# representative/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.representative_list_view, name='representative_list',),
    re_path(r'^edit_process/$', views_admin.representative_edit_process_view, name='representative_edit_process'),
    re_path(r'^delete/', views_admin.representative_delete_process_view, name='representative_delete_process'),
    # re_path(r'^import/$',
    #     views_admin.representatives_import_from_master_server_view,
    # name='representatives_import_from_master_server'),
    re_path(r'^new/$', views_admin.representative_new_view, name='representative_new'),
    re_path(r'^(?P<representative_id>[0-9]+)/edit/$', views_admin.representative_edit_view,
        name='representative_edit'),
    re_path(r'^(?P<representative_id>[0-9]+)/retrieve_photos/$',
        views_admin.representative_retrieve_photos_view, name='representative_retrieve_photos'),
]
