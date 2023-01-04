# candidate/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import re_path


urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.candidate_list_view, name='candidate_list',),
    re_path(r'^politician_match_this_election/', views_admin.candidate_politician_match_this_election_view,
        name='candidate_politician_match_for_this_election'),
    re_path(r'^edit_process/$', views_admin.candidate_edit_process_view, name='candidate_edit_process'),
    re_path(r'^merge/$', views_admin.candidate_merge_process_view, name='candidate_merge_process'),
    re_path(r'^delete/', views_admin.candidate_delete_process_view, name='candidate_delete_process'),
    re_path(r'^politician_match/', views_admin.candidate_politician_match_view, name='candidate_politician_match'),
    re_path(r'^import/$',
        views_admin.candidates_import_from_master_server_view, name='candidates_import_from_master_server'),
    re_path(r'^new/$', views_admin.candidate_new_view, name='candidate_new'),
    re_path(r'^new_search/$', views_admin.candidate_new_search_view, name='candidate_new_search'),
    re_path(r'^new_search_process/$',
            views_admin.candidate_new_search_process_view, name='candidate_new_search_process'),
    re_path(r'^(?P<candidate_id>[0-9]+)/edit/$', views_admin.candidate_edit_view, name='candidate_edit'),
    re_path(r'^(?P<candidate_we_vote_id>wv[\w]{2}cand[\w]+)/edit/$',
        views_admin.candidate_edit_view, name='candidate_edit_we_vote_id'),
    re_path(r'^(?P<candidate_id>[0-9]+)/find_duplicate_candidate/$',
        views_admin.find_duplicate_candidate_view, name='find_duplicate_candidate'),
    re_path(r'^(?P<candidate_id>[0-9]+)/retrieve_photos/$',
        views_admin.candidate_retrieve_photos_view, name='candidate_retrieve_photos'),
    re_path(r'^compare_two_candidates/$',
        views_admin.compare_two_candidates_for_merge_view, name='compare_two_candidates_for_merge'),
    re_path(r'^duplicate_candidates/$',
        views_admin.find_and_merge_duplicate_candidates_view, name='find_and_merge_duplicate_candidates'),
    re_path(r'^remove_duplicate_candidate/$',
        views_admin.remove_duplicate_candidate_view, name='remove_duplicate_candidate'),
    re_path(r'^(?P<election_id>[0-9]+)/photos_for_election/$',
        views_admin.retrieve_candidate_photos_for_election_view, name='photos_for_election'),
    re_path(r'^repair_imported_names/$', views_admin.repair_imported_names_view, name='repair_imported_names'),
    re_path(r'^(?P<candidate_id>[0-9]+)/summary/$', views_admin.candidate_summary_view,
        name='candidate_summary'),
]
