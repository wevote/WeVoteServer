# voter/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.voter_list_view, name='voter_list',),
    re_path(r'^authenticate_manually/$', views_admin.voter_authenticate_manually_view, name='authenticate_manually'),
    re_path(r'^authenticate_manually_process/$',
        views_admin.voter_authenticate_manually_process_view, name='authenticate_manually_process'),
    re_path(r'^create_dev_user/$', views_admin.create_dev_user_view, name='create_dev_user'),
    re_path(r'^delete_process/$', views_admin.voter_delete_process_view, name='voter_delete_process'),
    re_path(r'^edit_process/$', views_admin.voter_edit_process_view, name='voter_edit_process'),
    re_path(r'^edit/(?P<voter_we_vote_id>wv[\w]{2}voter[\w]+)$',
            views_admin.voter_edit_view, name='voter_edit_we_vote_id'),
    re_path(r'^finish_voter_merge/$', views_admin.finish_voter_merge_process_view, name='finish_voter_merge_process'),
    re_path(r'^login_complete/$', views_admin.login_complete_view, name='login_complete_view'),
    re_path(r'^process_maintenance_status_flags/$',
        views_admin.process_maintenance_status_flags_view, name='process_maintenance_status_flags'),
    re_path(r'^voter_change_authority/$',
        views_admin.voter_change_authority_process_view, name='voter_change_authority_process'),
    re_path(r'^voter_remove_facebook_auth_process/$',
        views_admin.voter_remove_facebook_auth_process_view, name='voter_remove_facebook_auth_process'),
    re_path(r'^(?P<voter_id>[0-9]+)/edit/$', views_admin.voter_edit_view, name='voter_edit'),
    re_path(r'^(?P<voter_id>[0-9]+)/summary/$', views_admin.voter_summary_view, name='voter_summary'),
    re_path(r'^(?P<voter_we_vote_id>wv[\w]{2}voter[\w]+)/summary/$',
            views_admin.voter_summary_view, name='voter_summary_we_vote_id'),
]
