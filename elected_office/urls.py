# elected_office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.elected_office_list_view, name='elected_office_list', ),
    re_path(r'^delete/$', views_admin.elected_office_delete_process_view, name='elected_office_delete_process'),
    re_path(r'^edit_process/$', views_admin.elected_office_edit_process_view, name='elected_office_edit_process'),
    re_path(r'^new/$', views_admin.elected_office_new_view, name='elected_office_new'),
    re_path(r'^update/$', views_admin.elected_office_update_view, name='elected_office_update'),
    re_path(r'^real_time_status/$', views_admin.elected_office_update_status, name='elected_office_update_status'),
    re_path(r'^(?P<elected_office_id>[0-9]+)/edit/$', views_admin.elected_office_edit_view, name='elected_office_edit'),
    re_path(r'^(?P<elected_office_id>[0-9]+)/summary/$', views_admin.elected_office_summary_view,
        name='elected_office_summary'),

]
