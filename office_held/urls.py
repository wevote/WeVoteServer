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
    re_path(r'^new/$', views_admin.office_held_new_view, name='office_held_new'),
    re_path(r'^update/$', views_admin.office_held_update_view, name='office_held_update'),
    re_path(r'^real_time_status/$', views_admin.office_held_update_status, name='office_held_update_status'),
    re_path(r'^(?P<office_held_id>[0-9]+)/edit/$', views_admin.office_held_edit_view, name='office_held_edit'),
    re_path(r'^(?P<office_held_id>[0-9]+)/summary/$', views_admin.office_held_summary_view,
        name='office_held_summary'),

]
