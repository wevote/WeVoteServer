# office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.office_list_view, name='office_list',),
    re_path(r'^office_list_process/$', views_admin.office_list_process_view, name='office_list_process'),
    re_path(r'^compare_two_offices/$',
        views_admin.compare_two_offices_for_merge_view, name='compare_two_offices_for_merge'),
    re_path(r'^delete/$', views_admin.office_delete_process_view, name='office_delete_process'),
    re_path(r'^(?P<office_id>[0-9]+)/find_duplicate_office/$',
        views_admin.find_duplicate_office_view, name='find_duplicate_office'),
    re_path(r'^duplicate_offices/$',
        views_admin.find_and_merge_duplicate_offices_view, name='find_and_merge_duplicate_offices'),
    re_path(r'^edit_process/$', views_admin.office_edit_process_view, name='office_edit_process'),
    re_path(r'^import/$',
        views_admin.offices_import_from_master_server_view, name='offices_import_from_master_server'),
    re_path(r'^merge/$', views_admin.office_merge_process_view, name='office_merge_process'),
    re_path(r'^new/$', views_admin.office_new_view, name='office_new'),
    re_path(r'^offices_copy/$',
        views_admin.offices_copy_to_another_election_view, name='offices_copy_to_another_election'),
    re_path(r'^(?P<office_id>[0-9]+)/edit/$', views_admin.office_edit_view, name='office_edit'),
    re_path(r'^(?P<contest_office_we_vote_id>wv[\w]{2}off[\w]+)/edit/$',
        views_admin.office_edit_view, name='office_edit_we_vote_id'),
    re_path(r'^(?P<office_id>[0-9]+)/summary/$', views_admin.office_summary_view, name='office_summary'),
    re_path(r'^(?P<contest_office_we_vote_id>wv[\w]{2}off[\w]+)/summary/$',
        views_admin.office_summary_view, name='office_summary_we_vote_id'),
]
