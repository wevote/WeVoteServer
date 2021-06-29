# position/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path
from . import views, views_admin

urlpatterns = [
    # views_admin.py
    re_path(r'^$', views_admin.position_list_view, name='position_list',),
    re_path(r'^delete/$', views_admin.position_delete_process_view, name='position_delete_process',),
    re_path(r'^edit_process/$', views_admin.position_edit_process_view, name='position_edit_process'),
    # re_path(r'^export/', views_admin.PositionsSyncOutView.as_view(), name='positions_export'),
    re_path(r'^import/$',
        views_admin.positions_import_from_master_server_view, name='positions_import_from_master_server'),
    re_path(r'^new/$', views_admin.position_new_view, name='position_new',),
    re_path(r'^relink_candidates_measures/$', views_admin.relink_candidates_measures_view,
        name='relink_candidates_measures'),
    re_path(r'^(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/edit/$', views_admin.position_edit_view, name='position_edit'),
    re_path(r'^(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/summary/$',
        views_admin.position_summary_view, name='position_summary'),
    re_path(r'^refresh_cached_position_info_for_election/',
        views_admin.refresh_cached_position_info_for_election_view,
        name='refresh_cached_position_info_for_election'),
    re_path(r'^refresh_positions_with_candidate_details/',
        views_admin.refresh_positions_with_candidate_details_for_election_view,
        name='refresh_positions_with_candidate_details_for_election'),
    re_path(r'^refresh_positions_with_office_details/',
        views_admin.refresh_positions_with_contest_office_details_for_election_view,
        name='refresh_positions_with_contest_office_details_for_election'),
    re_path(r'^refresh_positions_with_measure_details/',
        views_admin.refresh_positions_with_contest_measure_details_for_election_view,
        name='refresh_positions_with_contest_measure_details_for_election')
]
